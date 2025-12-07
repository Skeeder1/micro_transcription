"""
Event system for decoupled module communication.

This module implements a publish/subscribe pattern that allows modules to
communicate without direct imports, breaking circular dependencies.

Usage:
    from shared.events import EventBus, Events

    # Subscribe to an event
    EventBus.subscribe(Events.TRANSCRIPTION_COMPLETE, my_handler)

    # Publish an event
    EventBus.publish(Events.TRANSCRIPTION_COMPLETE, text="Hello world")

    # Unsubscribe
    EventBus.unsubscribe(Events.TRANSCRIPTION_COMPLETE, my_handler)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional
from shared.logger import log_info, log_warn, log_error


# =============================================================================
# Event Types
# =============================================================================

class Events(Enum):
    """All available events in the system."""

    # System state events
    SYSTEM_ACTIVATED = auto()        # System woke up (F9 ON)
    SYSTEM_DEACTIVATED = auto()      # System went to sleep (F9 OFF)
    DEEP_SLEEP_ENTERED = auto()      # Deep sleep mode activated

    # Recording events
    RECORDING_STARTED = auto()       # Microphone recording started (F8 ON)
    RECORDING_STOPPED = auto()       # Microphone recording stopped (F8 OFF)

    # Audio events
    VOICE_DETECTED = auto()          # Voice activity detected
    SILENCE_DETECTED = auto()        # Silence detected
    AUDIO_BUFFER_FULL = auto()       # Production buffer reached limit

    # Model events
    MODEL_LOADING_STARTED = auto()   # Whisper model loading started
    MODEL_LOADING_COMPLETE = auto()  # Whisper model loading finished
    MODEL_LOADING_FAILED = auto()    # Whisper model loading failed
    MODEL_UNLOADED = auto()          # Whisper model unloaded (deep sleep)

    # Transcription events
    TRANSCRIPTION_STARTED = auto()   # Whisper transcription started
    TRANSCRIPTION_COMPLETE = auto()  # Transcription finished with result
    TRANSCRIPTION_FAILED = auto()    # Transcription error

    # Preview events
    PREVIEW_UPDATED = auto()         # Preview text updated

    # UI events
    VISUALIZER_STARTED = auto()      # Visualizer window opened
    VISUALIZER_CLOSED = auto()       # Visualizer window closed

    # Calibration events
    CALIBRATION_STARTED = auto()     # VAD calibration started
    CALIBRATION_COMPLETE = auto()    # VAD calibration finished


# =============================================================================
# Event Data Classes
# =============================================================================

@dataclass(frozen=True)
class EventData:
    """Base class for event data."""
    pass


@dataclass(frozen=True)
class TranscriptionData(EventData):
    """Data for transcription events."""
    text: Optional[str] = None
    duration_seconds: float = 0.0
    is_preview: bool = False


@dataclass(frozen=True)
class AudioData(EventData):
    """Data for audio events."""
    rms: float = 0.0
    is_voice: bool = False
    silero_prob: float = 0.0


@dataclass(frozen=True)
class StateData(EventData):
    """Data for state change events."""
    previous_state: str = ""
    new_state: str = ""


@dataclass(frozen=True)
class CalibrationData(EventData):
    """Data for calibration events."""
    noise_floor: float = 0.0
    dynamic_threshold: float = 0.0


# =============================================================================
# Event Handler Type
# =============================================================================

EventHandler = Callable[..., None]


# =============================================================================
# EventBus Implementation
# =============================================================================

class _EventBus:
    """
    Thread-safe event bus for publish/subscribe pattern.

    Implements the singleton pattern - use EventBus instead of instantiating.
    """

    def __init__(self) -> None:
        self._handlers: Dict[Events, List[EventHandler]] = {}
        self._lock = threading.RLock()
        self._enabled = True

    def subscribe(
        self,
        event: Events,
        handler: EventHandler,
    ) -> None:
        """
        Subscribe a handler to an event.

        Args:
            event: The event type to subscribe to
            handler: Callback function to invoke when event is published
        """
        with self._lock:
            if event not in self._handlers:
                self._handlers[event] = []

            # Avoid duplicate subscriptions
            if handler not in self._handlers[event]:
                self._handlers[event].append(handler)

    def unsubscribe(self, event: Events, handler: EventHandler) -> None:
        """
        Unsubscribe a handler from an event.

        Args:
            event: The event type to unsubscribe from
            handler: The handler to remove
        """
        with self._lock:
            if event in self._handlers:
                try:
                    self._handlers[event].remove(handler)
                except ValueError:
                    pass  # Handler not found, ignore

    def unsubscribe_all(self, event: Optional[Events] = None) -> None:
        """
        Unsubscribe all handlers from an event or all events.

        Args:
            event: Specific event to clear, or None to clear all
        """
        with self._lock:
            if event is None:
                self._handlers.clear()
            elif event in self._handlers:
                self._handlers[event].clear()

    def publish(self, event: Events, **kwargs: Any) -> None:
        """
        Publish an event to all subscribed handlers.

        Args:
            event: The event type to publish
            **kwargs: Event data to pass to handlers
        """
        if not self._enabled:
            return

        with self._lock:
            handlers = self._handlers.get(event, []).copy()

        for handler in handlers:
            try:
                handler(**kwargs)
            except Exception as exc:
                log_error(f"[EventBus] Error in handler for {event.name}: {exc}")

    def publish_async(self, event: Events, **kwargs: Any) -> threading.Thread:
        """
        Publish an event asynchronously in a separate thread.

        Args:
            event: The event type to publish
            **kwargs: Event data to pass to handlers

        Returns:
            The thread executing the handlers
        """
        thread = threading.Thread(
            target=self.publish,
            args=(event,),
            kwargs=kwargs,
            daemon=True,
            name=f"Event-{event.name}"
        )
        thread.start()
        return thread

    def enable(self) -> None:
        """Enable event publishing."""
        self._enabled = True

    def disable(self) -> None:
        """Disable event publishing (handlers won't be called)."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Check if event publishing is enabled."""
        return self._enabled

    def get_handler_count(self, event: Events) -> int:
        """Get the number of handlers subscribed to an event."""
        with self._lock:
            return len(self._handlers.get(event, []))


# Singleton instance
EventBus = _EventBus()
