"""
Main audio processing loop.

Orchestrates the audio capture, voice detection, and transcription pipeline
using modular components for better maintainability.

This module uses dependency injection via the ServiceRegistry for decoupled
communication with the UI layer through the IBroadcaster interface.

Phase 4 Integration:
- Uses ServiceRegistry for broadcaster access (IBroadcaster)
- Publishes events via EventBus for all state transitions
- Applies error handling decorators for robust transcription
"""

from __future__ import annotations

import sys
import time
from queue import Empty
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np

from shared import config
from shared.constants import (
    LOG_PREFIX_DIAG,
    LOG_PREFIX_FORCE_FLUSH,
    DIAGNOSTIC_INTERVAL_SECONDS,
)
from shared.events import EventBus, Events
from shared.interfaces import IBroadcaster
from shared.logger import log_info, log_warn, log_error
from shared.errors import handle_errors
from shared.service_utils import get_broadcaster
from .audio_capture import detect_activity, paste_via_clipboard
from .audio_preprocessing import preprocess_audio
from .models import transcribe_preview, transcribe_production
from .phrase_detector import PhraseEndDetector
from .pipeline import AudioBuffer, PreviewManager, ProductionManager

if TYPE_CHECKING:
    from shared.context import AppContext


def _clear_line() -> None:
    """Clear current console line for real-time updates."""
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()


def _print_realtime(message: str) -> None:
    """Print real-time status without newline (for console feedback)."""
    sys.stdout.write(f"\r{message}")
    sys.stdout.flush()


# =============================================================================
# Main Processing Loop
# =============================================================================

def run(ctx: AppContext) -> None:
    """
    Stream microphone audio, manage preview and production outputs.

    This is the main entry point for the audio processing loop.
    Handles both visualizer-only and full transcription modes.
    """
    # Import sleep functions (still needed as they contain business logic)
    from shared.sleep import (
        check_auto_sleep, check_deep_sleep, check_visualizer_closed,
        is_sleeping, update_speech_timer
    )

    # Get broadcaster from service registry (replaces api.server imports)
    broadcaster = get_broadcaster()

    if not config.ENABLE_TRANSCRIPTION:
        _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep,
                            check_visualizer_closed, is_sleeping, update_speech_timer,
                            broadcaster)
    else:
        _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep,
                               check_visualizer_closed, is_sleeping,
                               update_speech_timer, broadcaster)


# =============================================================================
# Visualizer-Only Mode
# =============================================================================

def _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep,
                         check_visualizer_closed, is_sleeping, update_speech_timer,
                         broadcaster: Optional[IBroadcaster]):
    """
    Run in visualizer-only mode (no transcription).

    Simply captures audio for visualization and manages sleep state.
    Auto-wake is DISABLED - only F9 can wake from sleep.
    """
    _print_visualizer_banner()
    last_sleep_check = time.time()
    was_voice = False  # Track VAD state transitions

    try:
        while True:
            # Throttled sleep checks
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                check_visualizer_closed(ctx)
                last_sleep_check = time.time()

            # Handle sleep state - NO auto-wake, just drain queue
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                continue

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                continue

            # Detect voice and broadcast VAD state changes
            is_voice = detect_activity(audio_block, ctx.voice_detector)
            if is_voice != was_voice:
                if broadcaster:
                    broadcaster.send_vad(ctx, is_voice)
                # Publish voice detection event
                if is_voice:
                    EventBus.publish(Events.VOICE_DETECTED, is_voice=True)
                else:
                    EventBus.publish(Events.SILENCE_DETECTED, is_voice=False)
                was_voice = is_voice

            # Update speech timer on voice activity
            if is_voice:
                update_speech_timer(ctx)

    except KeyboardInterrupt:
        log_info("Arrêt du visualiseur...")


# =============================================================================
# Full Transcription Mode
# =============================================================================

def _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep,
                           check_visualizer_closed, is_sleeping,
                           update_speech_timer, broadcaster: Optional[IBroadcaster]):
    """
    Run full transcription mode with preview and production pipelines.

    Uses modular components for buffer management, preview timing,
    and production decisions.

    Auto-wake is DISABLED - only F9 can wake from sleep.
    Supports force_flush flag for F8 OFF and F9 OFF transcription.
    """
    # Initialize components
    buffer = AudioBuffer(
        max_production_seconds=getattr(config, 'MAX_PRODUCTION_SECONDS', 30.0),
        preview_window_seconds=config.PREVIEW_WINDOW_SECONDS,
        block_seconds=config.BLOCK_SECONDS,
    )

    phrase_detector = PhraseEndDetector(
        sample_rate=config.SAMPLE_RATE,
        history_size=getattr(config, 'ENERGY_HISTORY_BLOCKS', 5),
        energy_drop_threshold=getattr(config, 'ENERGY_DROP_THRESHOLD', 0.3),
    )

    preview_manager = PreviewManager(
        update_interval=config.PREVIEW_UPDATE_INTERVAL,
        timeout=config.PREVIEW_TIMEOUT,
    )

    production_manager = ProductionManager()

    _print_transcription_banner()
    last_sleep_check = time.time()
    was_voice = False  # Track VAD state transitions

    # Diagnostic counters
    diag_voice_count = 0
    diag_silence_count = 0
    diag_last_report = time.time()
    DIAG_INTERVAL = DIAGNOSTIC_INTERVAL_SECONDS  # Report interval from constants

    try:
        while True:
            # Check force_flush flag (set by F8 OFF or F9 OFF)
            if ctx.force_flush:
                _force_flush_buffer(ctx, buffer, phrase_detector, broadcaster)
                ctx.force_flush = False  # Clear flag

            # Throttled sleep checks
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                check_visualizer_closed(ctx)
                last_sleep_check = time.time()

            # Handle sleep state - NO auto-wake, just drain queue
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                continue

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                continue

            # Check bypass mode FIRST (before calling VAD)
            with ctx.vad_bypass_lock:
                bypass_enabled = ctx.vad_bypass

            if bypass_enabled:
                # === BYPASS MODE ===
                # Skip VAD entirely - record everything until F8
                is_voice = True
                raw_is_voice = True  # UI consistency
            else:
                # === NORMAL MODE ===
                # Use Silero VAD for voice detection
                raw_is_voice = detect_activity(audio_block, ctx.voice_detector)
                is_voice = raw_is_voice

            # Broadcast VAD state changes (reflects actual recording decision)
            # is_voice = True means audio goes to buffer (will be transcribed)
            # This works for both normal mode and bypass mode
            if is_voice != was_voice:
                if broadcaster:
                    broadcaster.send_vad(ctx, is_voice)
                # Publish voice detection event
                if is_voice:
                    EventBus.publish(Events.VOICE_DETECTED, is_voice=True)
                else:
                    EventBus.publish(Events.SILENCE_DETECTED, is_voice=False)
                was_voice = is_voice

            phrase_detector.update(audio_block, not is_voice)

            # Diagnostic: count voice/silence ratio
            if is_voice:
                diag_voice_count += 1
            else:
                diag_silence_count += 1

            # Periodic diagnostic report
            now = time.time()
            if now - diag_last_report >= DIAG_INTERVAL:
                total = diag_voice_count + diag_silence_count
                voice_pct = (diag_voice_count / total * 100) if total > 0 else 0
                delta_speech = now - ctx.last_speech_time
                log_info(
                    f"{LOG_PREFIX_DIAG} Voix: {diag_voice_count} ({voice_pct:.0f}%) | "
                    f"Silence: {diag_silence_count} | "
                    f"Buffer: {len(buffer._production)} blocks | "
                    f"Depuis parole: {delta_speech:.1f}s"
                )
                diag_voice_count = 0
                diag_silence_count = 0
                diag_last_report = now

            if is_voice:
                _handle_voice_activity(
                    ctx, audio_block, buffer, phrase_detector,
                    preview_manager, update_speech_timer, broadcaster
                )
            else:
                _handle_silence(
                    ctx, buffer, phrase_detector, production_manager, broadcaster
                )

    except KeyboardInterrupt:
        _handle_shutdown(ctx, buffer, broadcaster)


# =============================================================================
# Common Transcription Logic (deduplicated)
# =============================================================================

@handle_errors(log_prefix="[Transcribe]", reraise=False, default_return=None)
def _transcribe_and_paste(
    ctx,
    audio: "np.ndarray",
    broadcaster: Optional[IBroadcaster],
    status_message: str = "Transcription...",
    log_prefix: str = "[Transcription]"
) -> Optional[str]:
    """
    Common transcription and paste logic.

    Extracted to eliminate code duplication across:
    - _flush_production_overflow
    - _flush_production
    - _force_flush_buffer
    - _handle_shutdown

    Args:
        ctx: Application context
        audio: Raw audio data (will be preprocessed)
        broadcaster: Optional broadcaster for UI updates
        status_message: Message to show during transcription
        log_prefix: Prefix for log messages

    Returns:
        Transcribed text or None if no text detected
    """
    # Signal start
    if broadcaster:
        broadcaster.send_processing(ctx, True)

    # Preprocess audio
    audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)

    # Show status
    _clear_line()
    if broadcaster:
        broadcaster.send_preview(ctx, status_message)

    # Publish transcription started event
    EventBus.publish(Events.TRANSCRIPTION_STARTED)

    # Run transcription
    final_text = transcribe_production(ctx, audio)

    # Signal done
    if broadcaster:
        broadcaster.send_processing(ctx, False)

    # Handle result
    if final_text:
        log_info(f"{log_prefix} {final_text}")
        paste_via_clipboard(ctx, final_text)
        if broadcaster:
            broadcaster.send_preview(ctx, final_text)
        # Publish transcription complete event
        EventBus.publish(Events.TRANSCRIPTION_COMPLETE, text=final_text)
    else:
        if broadcaster:
            broadcaster.send_preview(ctx, "")

    return final_text


# =============================================================================
# Voice Activity Handling
# =============================================================================

def _handle_voice_activity(ctx, audio_block, buffer, phrase_detector,
                           preview_manager, update_speech_timer,
                           broadcaster: Optional[IBroadcaster]):
    """Handle audio block when voice is detected."""
    buffer.add_voice_audio(audio_block)
    update_speech_timer(ctx)

    # Check for buffer overflow (only if bypass is OFF)
    with ctx.vad_bypass_lock:
        bypass_on = ctx.vad_bypass

    if not bypass_on and buffer.is_production_overflow:
        _flush_production_overflow(ctx, buffer, phrase_detector, broadcaster)
        return

    # Update preview if enabled
    if config.ENABLE_PREVIEW and preview_manager.should_update():
        _update_preview(ctx, buffer, preview_manager, broadcaster)


def _flush_production_overflow(ctx, buffer, phrase_detector,
                               broadcaster: Optional[IBroadcaster]):
    """Handle production buffer overflow."""
    log_warn(f"Buffer limit ({getattr(config, 'MAX_PRODUCTION_SECONDS', 30)}s) - forcing transcription...")
    # Publish buffer overflow event
    EventBus.publish(Events.AUDIO_BUFFER_FULL)

    audio = buffer.get_production_audio()
    if audio is not None:
        _transcribe_and_paste(
            ctx, audio, broadcaster,
            status_message="Transcription (overflow)...",
            log_prefix="[Overflow]"
        )

    buffer.clear()
    phrase_detector.reset()


def _update_preview(ctx, buffer, preview_manager,
                    broadcaster: Optional[IBroadcaster]):
    """Update preview transcription."""
    audio = buffer.get_preview_audio()
    if audio is None:
        return

    audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=False)

    # Create a wrapper function for the preview manager
    def send_preview(ctx, text):
        if broadcaster:
            broadcaster.send_preview(ctx, text)

    preview_text = preview_manager.execute_preview(
        ctx, audio, transcribe_preview, send_preview
    )

    if preview_text:
        _print_realtime(f"Preview: {preview_text}")
        # Publish preview updated event
        EventBus.publish(Events.PREVIEW_UPDATED, text=preview_text)


# =============================================================================
# Silence Handling
# =============================================================================

def _handle_silence(ctx, buffer, phrase_detector, production_manager,
                    broadcaster: Optional[IBroadcaster]):
    """Handle audio block when silence is detected."""
    if not config.ENABLE_PRODUCTION or not buffer.has_production_audio:
        return

    buffer.add_silence()

    # Check if we should flush production
    should_flush = production_manager.should_flush(buffer, phrase_detector, is_silent=True)

    if should_flush:
        _flush_production(ctx, buffer, phrase_detector, broadcaster)


def _flush_production(ctx, buffer, phrase_detector,
                      broadcaster: Optional[IBroadcaster]):
    """Flush production buffer and transcribe."""
    audio = buffer.get_production_audio()
    if audio is None:
        return

    _transcribe_and_paste(
        ctx, audio, broadcaster,
        status_message="Transcription...",
        log_prefix="[Production]"
    )

    buffer.clear()
    phrase_detector.reset()


def _force_flush_buffer(ctx, buffer, phrase_detector,
                        broadcaster: Optional[IBroadcaster]):
    """
    Force immediate transcription of buffered audio.

    Called when F8 OFF or F9 OFF is pressed to transcribe
    whatever audio is currently in the buffer.
    """
    if not buffer.has_production_audio:
        log_info(f"{LOG_PREFIX_FORCE_FLUSH} Pas d'audio en buffer, skip")
        return

    log_info(f"{LOG_PREFIX_FORCE_FLUSH} TRANSCRIPTION FORCÉE (F8/F9 OFF)")

    audio = buffer.get_production_audio()
    if audio is None:
        return

    result = _transcribe_and_paste(
        ctx, audio, broadcaster,
        status_message="Transcription forcée...",
        log_prefix=LOG_PREFIX_FORCE_FLUSH
    )

    if not result:
        log_info(f"{LOG_PREFIX_FORCE_FLUSH} Pas de texte détecté")

    buffer.clear()
    phrase_detector.reset()
    log_info(f"{LOG_PREFIX_FORCE_FLUSH} Buffer vidé")


# =============================================================================
# Utility Functions
# =============================================================================

def _should_check_sleep(last_check: float, interval: float = 1.0) -> bool:
    """Check if enough time has passed for sleep checks."""
    return time.time() - last_check >= interval


def _drain_audio_queue(ctx) -> None:
    """Drain audio queue when sleeping (discard audio)."""
    try:
        ctx.audio_queue.get(timeout=0.1)
    except Empty:
        pass


def _get_audio_block(ctx):
    """Get next audio block from queue."""
    try:
        return ctx.audio_queue.get(timeout=0.1)
    except Empty:
        return None


def _handle_shutdown(ctx, buffer, broadcaster: Optional[IBroadcaster]):
    """Handle graceful shutdown with pending audio."""
    if config.ENABLE_PRODUCTION and buffer.has_production_audio:
        audio = buffer.get_production_audio()
        if audio is not None:
            _transcribe_and_paste(
                ctx, audio, broadcaster,
                status_message="Transcription finale...",
                log_prefix="[Shutdown]"
            )

    log_info("Arrêt du système de transcription...")


# =============================================================================
# Banner Messages
# =============================================================================

def _print_visualizer_banner() -> None:
    """Log startup banner for visualizer-only mode."""
    log_info("Visualiseur d'ondes actif (Ctrl+C pour quitter)")
    log_info("  Mode: Visualisation uniquement (transcription désactivée)")
    log_info("  F8: Pause/Reprendre micro | F9: Système ON/OFF")
    log_info(f"  Veille auto après {config.AUTO_SLEEP_SECONDS}s")


def _print_transcription_banner() -> None:
    """Log startup banner for transcription mode."""
    if config.ENABLE_PREVIEW:
        log_info("Écoute active (Ctrl+C pour quitter)")
        log_info("  Preview: Visualiseur (temps réel)")
        log_info("  Production: Curseur (modèle large)")
    else:
        log_info("Transcription directe active (Ctrl+C pour quitter)")
        log_info("  Modèle LARGE -> Transcription directe au curseur")

    log_info("  F8: Pause/Reprendre micro | F9: Système ON/OFF")
    log_info(f"  Veille auto après {config.AUTO_SLEEP_SECONDS}s")
