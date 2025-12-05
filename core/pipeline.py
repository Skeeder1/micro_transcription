"""
Audio processing pipeline components.

Provides reusable classes for managing audio buffers and orchestrating
the transcription process, separating concerns from the main processing loop.
"""

from __future__ import annotations

import time
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Optional, Callable, List, TYPE_CHECKING

import numpy as np

from shared import config

if TYPE_CHECKING:
    from shared.context import AppContext


# =============================================================================
# Audio Buffer Management
# =============================================================================

class AudioBuffer:
    """
    Manages preview and production audio buffers.

    Handles buffer accumulation, overflow protection, and buffer management
    for the dual-pipeline transcription architecture.
    """

    def __init__(
        self,
        max_production_seconds: float = 30.0,
        preview_window_seconds: float = 3.0,
        block_seconds: float = 0.5,
    ):
        """
        Initialize audio buffer.

        Args:
            max_production_seconds: Maximum production buffer duration (overflow protection)
            preview_window_seconds: Size of sliding preview window
            block_seconds: Duration of each audio block
        """
        self.max_production_seconds = max_production_seconds
        self.preview_window_seconds = preview_window_seconds
        self.block_seconds = block_seconds

        # Calculate block limits
        self.max_production_blocks = int(max_production_seconds / block_seconds)
        self.max_preview_blocks = int(preview_window_seconds / block_seconds)

        # Audio buffers
        self._preview: List[np.ndarray] = []
        self._production: List[np.ndarray] = []

        # State tracking
        self._silence_blocks: int = 0

    # -------------------------------------------------------------------------
    # Buffer Operations
    # -------------------------------------------------------------------------

    def add_voice_audio(self, audio_block: np.ndarray) -> None:
        """
        Add audio block when voice is detected.

        Args:
            audio_block: Audio samples to add
        """
        self._preview.append(audio_block)
        self._production.append(audio_block)
        self._silence_blocks = 0

        # Enforce preview window size (sliding window)
        if len(self._preview) > self.max_preview_blocks:
            self._preview.pop(0)

    def add_silence(self) -> None:
        """Record a silence block (voice not detected)."""
        self._silence_blocks += 1

    def clear(self) -> None:
        """Clear both buffers and reset silence counter."""
        self._preview.clear()
        self._production.clear()
        self._silence_blocks = 0

    def clear_preview(self) -> None:
        """Clear only preview buffer."""
        self._preview.clear()

    # -------------------------------------------------------------------------
    # Buffer State Queries
    # -------------------------------------------------------------------------

    @property
    def has_production_audio(self) -> bool:
        """Check if production buffer has content."""
        return len(self._production) > 0

    @property
    def has_preview_audio(self) -> bool:
        """Check if preview buffer has content."""
        return len(self._preview) > 0

    @property
    def is_production_overflow(self) -> bool:
        """Check if production buffer has reached maximum size."""
        return len(self._production) >= self.max_production_blocks

    @property
    def silence_blocks(self) -> int:
        """Get number of consecutive silence blocks."""
        return self._silence_blocks

    @property
    def production_duration(self) -> float:
        """Get approximate duration of production buffer in seconds."""
        return len(self._production) * self.block_seconds

    # -------------------------------------------------------------------------
    # Audio Extraction
    # -------------------------------------------------------------------------

    def get_preview_audio(self) -> Optional[np.ndarray]:
        """
        Get concatenated preview audio.

        Returns:
            Preview audio as single array, or None if empty
        """
        if not self._preview:
            return None
        return np.concatenate(self._preview, axis=0)

    def get_production_audio(self) -> Optional[np.ndarray]:
        """
        Get concatenated production audio.

        Returns:
            Production audio as single array, or None if empty
        """
        if not self._production:
            return None
        return np.concatenate(self._production, axis=0)


# =============================================================================
# Sleep State Manager
# =============================================================================

class SleepStateManager:
    """
    Manages sleep state checks with throttling.

    Consolidates sleep-related checks and ensures they aren't called
    too frequently, improving performance.
    """

    def __init__(self, check_interval: float = 1.0):
        """
        Initialize sleep state manager.

        Args:
            check_interval: Minimum interval between sleep checks (seconds)
        """
        self.check_interval = check_interval
        self._last_check_time: float = 0.0
        self._check_functions: List[Callable] = []

    def register_check(self, check_fn: Callable) -> None:
        """Register a sleep check function."""
        self._check_functions.append(check_fn)

    def should_check(self) -> bool:
        """Check if enough time has passed for another sleep check."""
        now = time.time()
        if now - self._last_check_time >= self.check_interval:
            self._last_check_time = now
            return True
        return False

    def run_checks(self, ctx: "AppContext") -> None:
        """Run all registered sleep checks."""
        for check_fn in self._check_functions:
            check_fn(ctx)


# =============================================================================
# Preview Manager
# =============================================================================

class PreviewManager:
    """
    Manages preview transcription timing and execution.

    Controls when preview updates should occur and handles
    preview transcription with timeout handling.
    """

    def __init__(
        self,
        update_interval: float = 0.8,
        timeout: float = 2.0,
    ):
        """
        Initialize preview manager.

        Args:
            update_interval: Minimum interval between preview updates
            timeout: Timeout for preview transcription
        """
        self.update_interval = update_interval
        self.timeout = timeout
        self._last_update_time: float = time.time()

    def should_update(self) -> bool:
        """Check if enough time has passed for preview update."""
        now = time.time()
        if now - self._last_update_time >= self.update_interval:
            return True
        return False

    def mark_updated(self) -> None:
        """Mark that preview was just updated."""
        self._last_update_time = time.time()

    def execute_preview(
        self,
        ctx: "AppContext",
        audio: np.ndarray,
        transcribe_fn: Callable,
        broadcast_fn: Callable,
    ) -> Optional[str]:
        """
        Execute preview transcription with timeout.

        Args:
            ctx: Application context
            audio: Audio to transcribe
            transcribe_fn: Function to transcribe audio
            broadcast_fn: Function to broadcast preview text

        Returns:
            Preview text if successful, None otherwise
        """
        future = ctx.executor.submit(transcribe_fn, ctx, audio)
        try:
            preview_text = future.result(timeout=self.timeout)
            if preview_text:
                broadcast_fn(ctx, preview_text)
                return preview_text
        except FuturesTimeoutError:
            print("\r⏱️ Preview timeout (skip)", end="", flush=True)
        except Exception as exc:
            print(f"\r⚠️ Preview error: {exc}", end="", flush=True)

        self.mark_updated()
        return None


# =============================================================================
# Production Manager
# =============================================================================

class ProductionManager:
    """
    Manages production transcription and pasting.

    Handles the decision of when to flush production buffer
    and execute final transcription.
    """

    def __init__(self):
        """Initialize production manager."""
        pass

    def should_flush(
        self,
        buffer: AudioBuffer,
        phrase_detector,
        is_silent: bool,
    ) -> bool:
        """
        Determine if production buffer should be flushed.

        Args:
            buffer: Audio buffer to check
            phrase_detector: Phrase end detector
            is_silent: Whether current frame is silent

        Returns:
            True if buffer should be flushed for transcription
        """
        if not buffer.has_production_audio:
            return False

        # Overflow protection
        if buffer.is_production_overflow:
            return True

        # Use phrase detection if enabled
        if getattr(config, 'ENABLE_PHRASE_DETECTION', True):
            return phrase_detector.is_phrase_end(is_silent)

        # Fallback to simple silence count
        return buffer.silence_blocks >= config.SILENCE_BLOCKS_BEFORE_FLUSH

    def execute_production(
        self,
        ctx: "AppContext",
        audio: np.ndarray,
        transcribe_fn: Callable,
        paste_fn: Callable,
        broadcast_fn: Callable,
    ) -> Optional[str]:
        """
        Execute production transcription and paste.

        Args:
            ctx: Application context
            audio: Audio to transcribe
            transcribe_fn: Function to transcribe audio
            paste_fn: Function to paste text
            broadcast_fn: Function to broadcast (clear preview)

        Returns:
            Final transcription text if successful
        """
        # Clear preview display
        print("\r" + " " * 80 + "\r", end="", flush=True)
        broadcast_fn(ctx, "")

        # Transcribe
        final_text = transcribe_fn(ctx, audio)

        if final_text:
            print(f"📋 {final_text}")
            paste_fn(ctx, final_text)

        return final_text
