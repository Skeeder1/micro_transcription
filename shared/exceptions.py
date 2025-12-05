"""
Custom exceptions for the transcription system.

Provides specific exception types for better error handling
and debugging across modules.
"""


class TranscriptionError(Exception):
    """Base exception for all transcription system errors."""
    pass


class ModelLoadError(TranscriptionError):
    """Raised when a model fails to load."""

    def __init__(self, model_name: str, reason: str = ""):
        self.model_name = model_name
        self.reason = reason
        message = f"Failed to load model '{model_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class AudioProcessingError(TranscriptionError):
    """Raised when audio processing fails."""

    def __init__(self, operation: str, reason: str = ""):
        self.operation = operation
        self.reason = reason
        message = f"Audio processing failed during '{operation}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class AudioCaptureError(TranscriptionError):
    """Raised when audio capture fails."""

    def __init__(self, device: str = "default", reason: str = ""):
        self.device = device
        self.reason = reason
        message = f"Failed to capture audio from device '{device}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class VADError(TranscriptionError):
    """Raised when voice activity detection fails."""

    def __init__(self, detector: str, reason: str = ""):
        self.detector = detector
        self.reason = reason
        message = f"VAD error in '{detector}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class PasteError(TranscriptionError):
    """Raised when clipboard paste operation fails."""

    def __init__(self, method: str = "clipboard", reason: str = ""):
        self.method = method
        self.reason = reason
        message = f"Paste failed using '{method}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class SSEError(TranscriptionError):
    """Raised when SSE communication fails."""

    def __init__(self, operation: str, reason: str = ""):
        self.operation = operation
        self.reason = reason
        message = f"SSE error during '{operation}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class ConfigurationError(TranscriptionError):
    """Raised when configuration is invalid."""

    def __init__(self, param: str, reason: str = ""):
        self.param = param
        self.reason = reason
        message = f"Invalid configuration for '{param}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class EnrollmentError(TranscriptionError):
    """Raised when speaker enrollment fails."""

    def __init__(self, reason: str = ""):
        self.reason = reason
        message = "Speaker enrollment failed"
        if reason:
            message += f": {reason}"
        super().__init__(message)
