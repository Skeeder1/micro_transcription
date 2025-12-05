"""
Shared application state container.

Organizes application state into logical sub-contexts for better
separation of concerns while maintaining a single entry point.
"""

from __future__ import annotations

import queue
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from faster_whisper import WhisperModel

from . import config

if TYPE_CHECKING:
    from core.voice_detector import VoiceDetector


# =============================================================================
# Sub-Contexts (logical groupings of related state)
# =============================================================================

@dataclass
class ModelContext:
    """
    Manages transcription models.

    Contains Whisper model and voice detector, with their associated
    locks for thread-safe access.
    """
    model: Optional[WhisperModel] = None
    model_lock: threading.Lock = field(default_factory=threading.Lock)
    voice_detector: Optional["VoiceDetector"] = None

    def has_model(self) -> bool:
        """Check if Whisper model is loaded."""
        return self.model is not None

    def has_voice_detector(self) -> bool:
        """Check if voice detector is available."""
        return self.voice_detector is not None


@dataclass
class SleepContext:
    """
    Manages sleep/wake state.

    Tracks whether the application is sleeping, deep sleeping,
    and related timing information.
    """
    is_sleeping: bool = False
    is_deep_sleeping: bool = False
    sleep_start_time: float = 0.0
    last_speech_time: float = field(default_factory=time.time)
    last_toggle_time: float = 0.0
    manual_sleep: bool = False
    sleep_lock: threading.Lock = field(default_factory=threading.Lock)

    def enter_sleep(self, manual: bool = False) -> None:
        """Enter sleep mode."""
        with self.sleep_lock:
            self.is_sleeping = True
            self.sleep_start_time = time.time()
            self.manual_sleep = manual

    def exit_sleep(self) -> None:
        """Exit sleep mode."""
        with self.sleep_lock:
            self.is_sleeping = False
            self.is_deep_sleeping = False
            self.manual_sleep = False

    def enter_deep_sleep(self) -> None:
        """Enter deep sleep mode (models unloaded)."""
        with self.sleep_lock:
            self.is_deep_sleeping = True

    def update_speech_time(self) -> None:
        """Update last speech time to now."""
        self.last_speech_time = time.time()


@dataclass
class AudioContext:
    """
    Manages audio capture state.

    Contains the audio queue and related state for audio processing.
    """
    audio_queue: queue.Queue = field(default_factory=queue.Queue)
    last_pasted: str = ""

    def clear_queue(self) -> None:
        """Clear all pending audio blocks."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break


@dataclass
class UIContext:
    """
    Manages UI state.

    Contains visualizer process and SSE client connections.
    """
    visualizer_proc: Optional[subprocess.Popen] = None
    visualizer_lock: threading.Lock = field(default_factory=threading.Lock)
    sse_clients: List[queue.Queue] = field(default_factory=list)
    sse_lock: threading.Lock = field(default_factory=threading.Lock)

    def is_visualizer_running(self) -> bool:
        """Check if visualizer process is running."""
        if self.visualizer_proc is None:
            return False
        return self.visualizer_proc.poll() is None

    def add_sse_client(self, client_queue: queue.Queue) -> None:
        """Add an SSE client queue."""
        with self.sse_lock:
            self.sse_clients.append(client_queue)

    def remove_sse_client(self, client_queue: queue.Queue) -> None:
        """Remove an SSE client queue."""
        with self.sse_lock:
            if client_queue in self.sse_clients:
                self.sse_clients.remove(client_queue)


# =============================================================================
# Main Application Context
# =============================================================================

@dataclass
class AppContext:
    """
    Mutable state shared across modules.

    This class provides both:
    1. Direct access to commonly used fields (for compatibility)
    2. Sub-context objects for organized access

    The sub-contexts (models, sleep, audio, ui) group related state
    and provide helper methods for common operations.
    """

    # =========================================================================
    # Sub-contexts for organized access
    # =========================================================================
    models: ModelContext = field(default_factory=ModelContext)
    sleep: SleepContext = field(default_factory=SleepContext)
    audio: AudioContext = field(default_factory=AudioContext)
    ui: UIContext = field(default_factory=UIContext)

    # =========================================================================
    # Direct field access (for backwards compatibility)
    # These delegate to sub-contexts
    # =========================================================================

    executor: ThreadPoolExecutor = field(init=False)

    def __post_init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=config.EXECUTOR_MAX_WORKERS)

    # -------------------------------------------------------------------------
    # Model properties (delegate to models sub-context)
    # -------------------------------------------------------------------------

    @property
    def model(self) -> Optional[WhisperModel]:
        return self.models.model

    @model.setter
    def model(self, value: Optional[WhisperModel]) -> None:
        self.models.model = value

    @property
    def model_lock(self) -> threading.Lock:
        return self.models.model_lock

    @property
    def voice_detector(self) -> Optional["VoiceDetector"]:
        return self.models.voice_detector

    @voice_detector.setter
    def voice_detector(self, value: Optional["VoiceDetector"]) -> None:
        self.models.voice_detector = value

    # -------------------------------------------------------------------------
    # Sleep properties (delegate to sleep sub-context)
    # -------------------------------------------------------------------------

    @property
    def is_sleeping(self) -> bool:
        return self.sleep.is_sleeping

    @is_sleeping.setter
    def is_sleeping(self, value: bool) -> None:
        self.sleep.is_sleeping = value

    @property
    def is_deep_sleeping(self) -> bool:
        return self.sleep.is_deep_sleeping

    @is_deep_sleeping.setter
    def is_deep_sleeping(self, value: bool) -> None:
        self.sleep.is_deep_sleeping = value

    @property
    def sleep_start_time(self) -> float:
        return self.sleep.sleep_start_time

    @sleep_start_time.setter
    def sleep_start_time(self, value: float) -> None:
        self.sleep.sleep_start_time = value

    @property
    def last_speech_time(self) -> float:
        return self.sleep.last_speech_time

    @last_speech_time.setter
    def last_speech_time(self, value: float) -> None:
        self.sleep.last_speech_time = value

    @property
    def last_toggle_time(self) -> float:
        return self.sleep.last_toggle_time

    @last_toggle_time.setter
    def last_toggle_time(self, value: float) -> None:
        self.sleep.last_toggle_time = value

    @property
    def manual_sleep(self) -> bool:
        return self.sleep.manual_sleep

    @manual_sleep.setter
    def manual_sleep(self, value: bool) -> None:
        self.sleep.manual_sleep = value

    @property
    def sleep_lock(self) -> threading.Lock:
        return self.sleep.sleep_lock

    # -------------------------------------------------------------------------
    # Audio properties (delegate to audio sub-context)
    # -------------------------------------------------------------------------

    @property
    def audio_queue(self) -> queue.Queue:
        return self.audio.audio_queue

    @property
    def last_pasted(self) -> str:
        return self.audio.last_pasted

    @last_pasted.setter
    def last_pasted(self, value: str) -> None:
        self.audio.last_pasted = value

    # -------------------------------------------------------------------------
    # UI properties (delegate to ui sub-context)
    # -------------------------------------------------------------------------

    @property
    def visualizer_proc(self) -> Optional[subprocess.Popen]:
        return self.ui.visualizer_proc

    @visualizer_proc.setter
    def visualizer_proc(self, value: Optional[subprocess.Popen]) -> None:
        self.ui.visualizer_proc = value

    @property
    def visualizer_lock(self) -> threading.Lock:
        return self.ui.visualizer_lock

    @property
    def sse_clients(self) -> List[queue.Queue]:
        return self.ui.sse_clients

    @property
    def sse_lock(self) -> threading.Lock:
        return self.ui.sse_lock

    # =========================================================================
    # Lifecycle Methods
    # =========================================================================

    def shutdown(self) -> None:
        """Release unmanaged resources."""
        self.executor.shutdown(wait=False)
