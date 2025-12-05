"""
Protocol definitions for audio detectors.

Defines interfaces for voice activity detection, phrase detection,
and speaker verification. Using Protocols (PEP 544) allows for
structural subtyping - classes don't need to explicitly inherit
from these protocols to be compatible.
"""

from typing import Protocol, Tuple, Dict, Any, Optional, runtime_checkable
from dataclasses import dataclass
import numpy as np


# =============================================================================
# Result Data Classes
# =============================================================================

@dataclass
class VoiceDetectionResult:
    """Result of voice activity detection."""
    is_voice: bool
    probability: float
    rms: float
    zcr: float
    boost_factor: float = 1.0

    def __repr__(self) -> str:
        return (
            f"VoiceDetectionResult(is_voice={self.is_voice}, "
            f"prob={self.probability:.3f}, rms={self.rms:.4f})"
        )


@dataclass
class PhraseDetectionResult:
    """Result of phrase end detection."""
    is_phrase_end: bool
    confidence: float
    silence_count: int
    had_speech: bool

    def __repr__(self) -> str:
        return (
            f"PhraseDetectionResult(end={self.is_phrase_end}, "
            f"conf={self.confidence:.2f})"
        )


@dataclass
class SpeakerVerificationResult:
    """Result of speaker verification."""
    is_user: bool
    similarity_score: float
    is_enrolled: bool

    def __repr__(self) -> str:
        return (
            f"SpeakerVerificationResult(is_user={self.is_user}, "
            f"score={self.similarity_score:.3f})"
        )


# =============================================================================
# Protocol Definitions
# =============================================================================

@runtime_checkable
class VoiceActivityDetector(Protocol):
    """
    Protocol for voice activity detection.

    Implementations detect whether an audio segment contains human speech
    as opposed to silence, background noise, or other non-speech sounds.
    """

    def is_human_speech(self, audio: np.ndarray, debug: bool = False) -> bool:
        """
        Detect if audio contains human speech.

        Args:
            audio: Audio samples as numpy array
            debug: Enable debug output

        Returns:
            True if human speech detected, False otherwise
        """
        ...

    def get_metrics(self) -> Dict[str, float]:
        """
        Get metrics from the last detection.

        Returns:
            Dictionary containing detection metrics like RMS, ZCR,
            probability scores, etc.
        """
        ...


@runtime_checkable
class PhraseEndDetector(Protocol):
    """
    Protocol for phrase/sentence end detection.

    Implementations detect natural breaks in speech, useful for
    determining when to finalize transcription.
    """

    def update(self, audio_block: np.ndarray, is_silent: bool) -> None:
        """
        Update detector state with new audio block.

        Args:
            audio_block: New audio samples
            is_silent: Whether this block is considered silent
        """
        ...

    def is_phrase_end(self, is_silent: bool) -> bool:
        """
        Check if current position is end of phrase.

        Args:
            is_silent: Whether current block is silent

        Returns:
            True if phrase end detected
        """
        ...

    def reset(self) -> None:
        """Reset detector state for new phrase."""
        ...

    def get_metrics(self) -> Dict[str, Any]:
        """Get current detection metrics."""
        ...


@runtime_checkable
class SpeakerVerifier(Protocol):
    """
    Protocol for speaker verification.

    Implementations verify if the current speaker matches an enrolled
    user profile, useful for filtering out other voices.
    """

    def is_user_speaking(
        self, audio: np.ndarray, debug: bool = False
    ) -> Tuple[bool, float]:
        """
        Check if audio matches enrolled user voice.

        Args:
            audio: Audio samples
            debug: Enable debug output

        Returns:
            Tuple of (is_user, similarity_score)
        """
        ...

    @property
    def is_enrolled(self) -> bool:
        """Check if a user voice profile is enrolled."""
        ...

    def add_enrollment_sample(self, audio: np.ndarray) -> int:
        """
        Add audio sample for enrollment.

        Args:
            audio: Audio sample to add

        Returns:
            Number of samples collected so far
        """
        ...

    def complete_enrollment(self) -> bool:
        """
        Complete enrollment process.

        Returns:
            True if enrollment successful
        """
        ...

    def reset_enrollment(self) -> None:
        """Reset enrollment data."""
        ...


@runtime_checkable
class TranscriptionBackend(Protocol):
    """
    Protocol for transcription backends.

    Implementations convert audio to text using speech recognition.
    """

    def transcribe(
        self,
        audio: np.ndarray,
        language: Optional[str] = None,
        initial_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """
        Transcribe audio to text.

        Args:
            audio: Audio samples
            language: Language code (e.g., 'fr', 'en')
            initial_prompt: Context prompt to guide transcription

        Returns:
            Transcribed text or None if failed
        """
        ...


@runtime_checkable
class ClipboardBackend(Protocol):
    """
    Protocol for clipboard operations.

    Implementations handle copying text to clipboard and pasting.
    """

    def copy(self, text: str) -> bool:
        """
        Copy text to clipboard.

        Args:
            text: Text to copy

        Returns:
            True if successful
        """
        ...

    def paste(self) -> bool:
        """
        Trigger paste operation.

        Returns:
            True if successful
        """
        ...

    def get_content(self) -> Optional[str]:
        """
        Get current clipboard content.

        Returns:
            Clipboard text or None
        """
        ...


# =============================================================================
# Type Aliases for Convenience
# =============================================================================

# For type hints when any detector is acceptable
AnyDetector = VoiceActivityDetector | PhraseEndDetector | SpeakerVerifier
