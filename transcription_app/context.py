"""Shared application state container."""

from __future__ import annotations

import queue
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import List, Optional

from faster_whisper import WhisperModel

from . import config


@dataclass
class AppContext:
    """Mutable state shared across modules."""

    visualizer_proc: Optional[subprocess.Popen] = None
    visualizer_lock: threading.Lock = field(default_factory=threading.Lock)

    preview_model: Optional[WhisperModel] = None
    production_model: Optional[WhisperModel] = None
    model_lock: threading.Lock = field(default_factory=threading.Lock)

    sse_clients: List[queue.Queue] = field(default_factory=list)
    sse_lock: threading.Lock = field(default_factory=threading.Lock)

    executor: ThreadPoolExecutor = field(init=False)
    audio_queue: queue.Queue = field(default_factory=queue.Queue)

    is_sleeping: bool = False
    is_deep_sleeping: bool = False
    sleep_start_time: float = 0.0  # Timestamp du début de veille
    sleep_lock: threading.Lock = field(default_factory=threading.Lock)
    last_speech_time: float = field(default_factory=time.time)
    last_toggle_time: float = 0.0
    manual_sleep: bool = False

    last_pasted: str = ""

    def __post_init__(self) -> None:
        self.executor = ThreadPoolExecutor(max_workers=config.EXECUTOR_MAX_WORKERS)

    def shutdown(self) -> None:
        """Release unmanaged resources."""
        self.executor.shutdown(wait=False)
