"""
Interface definitions for dependency injection.

This module defines Protocol classes that specify contracts between modules,
enabling loose coupling and easier testing through dependency injection.

Usage:
    from shared.interfaces import IBroadcaster, ITranscriber

    def process_audio(broadcaster: IBroadcaster, transcriber: ITranscriber):
        text = transcriber.transcribe(audio)
        broadcaster.send_preview(text)
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Optional, Protocol, runtime_checkable

import numpy as np

if TYPE_CHECKING:
    from shared.context import AppContext


# =============================================================================
# Broadcasting Interface
# =============================================================================

@runtime_checkable
class IBroadcaster(Protocol):
    """Interface for broadcasting messages to clients."""

    @abstractmethod
    def send_preview(self, ctx: "AppContext", text: str) -> None:
        """Send preview text to all connected clients."""
        ...

    @abstractmethod
    def send_state(self, ctx: "AppContext", state: str) -> None:
        """Send state change to all connected clients."""
        ...

    @abstractmethod
    def send_vad(self, ctx: "AppContext", is_voice: bool) -> None:
        """Send VAD state to all connected clients."""
        ...

    @abstractmethod
    def send_processing(self, ctx: "AppContext", is_processing: bool) -> None:
        """Send processing state to all connected clients."""
        ...

    @abstractmethod
    def send_recording(self, ctx: "AppContext", is_recording: bool) -> None:
        """Send recording state to all connected clients."""
        ...


# =============================================================================
# Transcription Interface
# =============================================================================

@runtime_checkable
class ITranscriber(Protocol):
    """Interface for audio transcription."""

    @abstractmethod
    def transcribe(self, audio: np.ndarray, is_preview: bool = False) -> Optional[str]:
        """
        Transcribe audio to text.

        Args:
            audio: Audio samples as numpy array
            is_preview: True for preview (fast), False for production

        Returns:
            Transcribed text or None if no speech detected
        """
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """Check if the transcriber is ready (model loaded)."""
        ...


# =============================================================================
# Voice Activity Detection Interface
# =============================================================================

@runtime_checkable
class IVoiceDetector(Protocol):
    """Interface for voice activity detection."""

    @abstractmethod
    def is_speech(self, audio: np.ndarray) -> bool:
        """
        Detect if audio contains human speech.

        Args:
            audio: Audio samples as numpy array

        Returns:
            True if speech detected, False otherwise
        """
        ...

    @abstractmethod
    def get_probability(self, audio: np.ndarray) -> float:
        """
        Get voice probability for audio.

        Args:
            audio: Audio samples as numpy array

        Returns:
            Probability of speech (0.0 to 1.0)
        """
        ...

    @abstractmethod
    def start_calibration(self) -> None:
        """Start/restart noise floor calibration."""
        ...

    @abstractmethod
    def skip_calibration(self) -> None:
        """Skip calibration and use existing values."""
        ...


# =============================================================================
# Audio Capture Interface
# =============================================================================

@runtime_checkable
class IAudioCapture(Protocol):
    """Interface for audio capture control."""

    @abstractmethod
    def start(self) -> None:
        """Start audio capture."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop audio capture."""
        ...

    @abstractmethod
    def is_recording(self) -> bool:
        """Check if currently recording."""
        ...

    @abstractmethod
    def set_recording(self, enabled: bool) -> None:
        """Enable or disable recording."""
        ...

    @abstractmethod
    def toggle_recording(self) -> bool:
        """Toggle recording state and return new state."""
        ...


# =============================================================================
# Visualizer Interface
# =============================================================================

@runtime_checkable
class IVisualizer(Protocol):
    """Interface for visualizer management."""

    @abstractmethod
    def start(self) -> None:
        """Start the visualizer."""
        ...

    @abstractmethod
    def stop(self) -> None:
        """Stop the visualizer."""
        ...

    @abstractmethod
    def is_running(self) -> bool:
        """Check if visualizer is running."""
        ...


# =============================================================================
# Sleep Manager Interface
# =============================================================================

@runtime_checkable
class ISleepManager(Protocol):
    """Interface for sleep state management."""

    @abstractmethod
    def activate(self) -> None:
        """Activate the system (wake from sleep)."""
        ...

    @abstractmethod
    def deactivate(self) -> None:
        """Deactivate the system (enter sleep)."""
        ...

    @abstractmethod
    def toggle(self) -> None:
        """Toggle between active and sleep states."""
        ...

    @abstractmethod
    def is_sleeping(self) -> bool:
        """Check if system is in sleep mode."""
        ...

    @abstractmethod
    def is_deep_sleeping(self) -> bool:
        """Check if system is in deep sleep mode."""
        ...


# =============================================================================
# Model Manager Interface
# =============================================================================

@runtime_checkable
class IModelManager(Protocol):
    """Interface for ML model management."""

    @abstractmethod
    def load_models(self) -> None:
        """Load all required models."""
        ...

    @abstractmethod
    def unload_models(self) -> None:
        """Unload models to free memory."""
        ...

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if models are loaded."""
        ...


# =============================================================================
# Audio Preprocessor Interface
# =============================================================================

@runtime_checkable
class IAudioPreprocessor(Protocol):
    """Interface for audio preprocessing operations.

    Provides a standard contract for audio preprocessing, enabling
    different implementations (e.g., noise reduction, normalization)
    to be swapped without changing dependent code.
    """

    @abstractmethod
    def preprocess(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000,
        for_production: bool = False
    ) -> np.ndarray:
        """
        Preprocess audio for transcription.

        Args:
            audio: Raw audio samples as numpy array
            sample_rate: Audio sample rate (default 16000Hz)
            for_production: True for production quality, False for preview

        Returns:
            Preprocessed audio samples
        """
        ...

    @abstractmethod
    def apply_noise_reduction(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """
        Apply noise reduction to audio.

        Args:
            audio: Raw audio samples
            sample_rate: Audio sample rate

        Returns:
            Audio with noise reduced
        """
        ...

    @abstractmethod
    def normalize(self, audio: np.ndarray) -> np.ndarray:
        """
        Normalize audio levels.

        Args:
            audio: Raw audio samples

        Returns:
            Normalized audio samples
        """
        ...


# =============================================================================
# Phrase Detector Interface
# =============================================================================

@runtime_checkable
class IPhraseDetector(Protocol):
    """Interface for phrase/sentence end detection.

    Used to determine when a speaker has finished a thought
    and transcription should be finalized.
    """

    @abstractmethod
    def update(self, audio: np.ndarray, is_silence: bool) -> None:
        """
        Update detector state with new audio.

        Args:
            audio: Audio samples
            is_silence: Whether current block is silence
        """
        ...

    @abstractmethod
    def is_phrase_end(self) -> bool:
        """
        Check if current state indicates end of phrase.

        Returns:
            True if phrase end detected
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset detector state for new phrase."""
        ...


# =============================================================================
# Service Locator Pattern (Alternative to DI Container)
# =============================================================================

class ServiceRegistry:
    """
    Simple service registry for runtime service location.

    This provides a lightweight alternative to full DI containers
    while still allowing loose coupling between modules.

    Usage:
        # Register a service
        ServiceRegistry.register(IBroadcaster, my_broadcaster)

        # Retrieve a service
        broadcaster = ServiceRegistry.get(IBroadcaster)
    """

    _services: dict[type, object] = {}

    @classmethod
    def register(cls, interface: type, implementation: object) -> None:
        """
        Register a service implementation.

        Args:
            interface: The interface/protocol type
            implementation: The implementation instance
        """
        cls._services[interface] = implementation

    @classmethod
    def get(cls, interface: type) -> Optional[object]:
        """
        Get a registered service.

        Args:
            interface: The interface/protocol type

        Returns:
            The implementation or None if not registered
        """
        return cls._services.get(interface)

    @classmethod
    def unregister(cls, interface: type) -> None:
        """
        Unregister a service.

        Args:
            interface: The interface/protocol type to unregister
        """
        cls._services.pop(interface, None)

    @classmethod
    def clear(cls) -> None:
        """Clear all registered services."""
        cls._services.clear()

    @classmethod
    def clear_all(cls) -> None:
        """Clear all registered services (alias for clear)."""
        cls.clear()

    @classmethod
    def is_registered(cls, interface: type) -> bool:
        """Check if a service is registered."""
        return interface in cls._services

    @classmethod
    def get_all(cls) -> dict[type, object]:
        """Get all registered services."""
        return cls._services.copy()


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Core interfaces
    "IBroadcaster",
    "ITranscriber",
    "IVoiceDetector",
    "IAudioCapture",
    "IVisualizer",
    "ISleepManager",
    "IModelManager",
    # New interfaces (Phase 5)
    "IAudioPreprocessor",
    "IPhraseDetector",
    # Service registry
    "ServiceRegistry",
]
