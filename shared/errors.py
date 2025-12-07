"""Centralized error handling system with decorators and utilities.

This module provides:
- Custom exception hierarchy for domain-specific errors
- Decorators for consistent error handling across the codebase
- Context managers for error aggregation
- Retry mechanisms with exponential backoff
- Thread-safe error collection and reporting

Usage:
    # Using decorators
    @handle_errors(log_prefix="[Audio]", reraise=False)
    def process_audio(data):
        ...

    # Using retry decorator
    @retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
    def connect_to_service():
        ...

    # Using error context
    with ErrorContext("audio_processing") as ctx:
        result = process_data()
        if ctx.has_errors:
            handle_errors(ctx.errors)
"""

from __future__ import annotations

import functools
import threading
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from shared.logger import log_error, log_warn, log_info


# =============================================================================
# Exception Hierarchy
# =============================================================================

class TranscriptionError(Exception):
    """Base exception for all transcription-related errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause
        self.timestamp = datetime.now()

    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


class AudioError(TranscriptionError):
    """Errors related to audio capture or processing."""
    pass


class AudioCaptureError(AudioError):
    """Failed to capture audio from device."""
    pass


class AudioProcessingError(AudioError):
    """Failed to process audio data."""
    pass


class ModelError(TranscriptionError):
    """Errors related to AI models."""
    pass


class ModelLoadError(ModelError):
    """Failed to load AI model."""
    pass


class ModelInferenceError(ModelError):
    """Failed during model inference."""
    pass


class ConfigurationError(TranscriptionError):
    """Invalid configuration or settings."""
    pass


class CommunicationError(TranscriptionError):
    """Errors related to inter-process communication."""
    pass


class SSEError(CommunicationError):
    """Server-Sent Events communication error."""
    pass


class VisualizerError(CommunicationError):
    """Visualizer subprocess error."""
    pass


class StateError(TranscriptionError):
    """Invalid state transition or state-related error."""
    pass


class ResourceError(TranscriptionError):
    """Resource allocation or management error."""
    pass


# =============================================================================
# Error Severity
# =============================================================================

class ErrorSeverity(Enum):
    """Severity levels for errors."""
    DEBUG = auto()      # Debugging information
    INFO = auto()       # Informational, not an error
    WARNING = auto()    # Warning, operation continues
    ERROR = auto()      # Error, operation may fail
    CRITICAL = auto()   # Critical, system may be unstable


# =============================================================================
# Error Record
# =============================================================================

@dataclass
class ErrorRecord:
    """Record of an error occurrence with context."""
    exception: Exception
    timestamp: datetime = field(default_factory=datetime.now)
    context: str = ""
    severity: ErrorSeverity = ErrorSeverity.ERROR
    traceback_str: str = ""
    thread_name: str = field(default_factory=lambda: threading.current_thread().name)

    def __post_init__(self) -> None:
        if not self.traceback_str:
            self.traceback_str = traceback.format_exc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "exception_type": type(self.exception).__name__,
            "message": str(self.exception),
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "severity": self.severity.name,
            "thread": self.thread_name,
        }


# =============================================================================
# Error Collector (Thread-Safe)
# =============================================================================

class ErrorCollector:
    """Thread-safe collector for aggregating errors.

    Useful for collecting errors across multiple operations and
    reporting them together.
    """

    def __init__(self, max_errors: int = 100) -> None:
        self._errors: List[ErrorRecord] = []
        self._lock = threading.Lock()
        self._max_errors = max_errors

    def add(
        self,
        exception: Exception,
        context: str = "",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
    ) -> None:
        """Add an error record."""
        with self._lock:
            if len(self._errors) >= self._max_errors:
                # Remove oldest error to make room
                self._errors.pop(0)
            self._errors.append(ErrorRecord(
                exception=exception,
                context=context,
                severity=severity,
            ))

    def get_errors(
        self,
        severity: Optional[ErrorSeverity] = None,
        context: Optional[str] = None,
    ) -> List[ErrorRecord]:
        """Get errors, optionally filtered by severity or context."""
        with self._lock:
            errors = self._errors.copy()

        if severity:
            errors = [e for e in errors if e.severity == severity]
        if context:
            errors = [e for e in errors if context in e.context]

        return errors

    def clear(self) -> None:
        """Clear all collected errors."""
        with self._lock:
            self._errors.clear()

    @property
    def has_errors(self) -> bool:
        """Check if any errors have been collected."""
        with self._lock:
            return len(self._errors) > 0

    @property
    def error_count(self) -> int:
        """Get the number of collected errors."""
        with self._lock:
            return len(self._errors)

    def get_summary(self) -> str:
        """Get a summary of collected errors."""
        with self._lock:
            if not self._errors:
                return "No errors collected"

            by_severity = {}
            for error in self._errors:
                key = error.severity.name
                by_severity[key] = by_severity.get(key, 0) + 1

            parts = [f"{k}: {v}" for k, v in sorted(by_severity.items())]
            return f"Errors: {', '.join(parts)}"


# Global error collector instance
_global_collector = ErrorCollector()


def get_global_collector() -> ErrorCollector:
    """Get the global error collector instance."""
    return _global_collector


# =============================================================================
# Error Context Manager
# =============================================================================

@dataclass
class ErrorContext:
    """Context manager for error handling with automatic collection.

    Usage:
        with ErrorContext("audio_processing") as ctx:
            process_audio()

        if ctx.has_errors:
            log_error(ctx.get_summary())
    """
    name: str
    collector: ErrorCollector = field(default_factory=ErrorCollector)
    suppress_exceptions: bool = False
    log_on_exit: bool = True

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Any,
    ) -> bool:
        if exc_val is not None and isinstance(exc_val, Exception):
            self.collector.add(exc_val, context=self.name)
            if self.log_on_exit:
                log_error(f"[{self.name}] {exc_val}")

        return self.suppress_exceptions

    @property
    def has_errors(self) -> bool:
        return self.collector.has_errors

    @property
    def errors(self) -> List[ErrorRecord]:
        return self.collector.get_errors()

    def get_summary(self) -> str:
        return self.collector.get_summary()


# =============================================================================
# Decorators
# =============================================================================

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def handle_errors(
    log_prefix: str = "",
    reraise: bool = True,
    default_return: Any = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    collect: bool = True,
) -> Callable[[F], F]:
    """Decorator for consistent error handling.

    Args:
        log_prefix: Prefix for log messages (e.g., "[Audio]")
        reraise: Whether to re-raise the exception after logging
        default_return: Value to return if exception is caught and not reraised
        exceptions: Tuple of exception types to catch
        severity: Severity level for logging
        collect: Whether to add errors to global collector

    Usage:
        @handle_errors(log_prefix="[Audio]", reraise=False)
        def process_audio(data):
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exceptions as exc:
                prefix = f"{log_prefix} " if log_prefix else ""
                message = f"{prefix}{func.__name__}: {exc}"

                if severity == ErrorSeverity.WARNING:
                    log_warn(message)
                elif severity.value >= ErrorSeverity.ERROR.value:
                    log_error(message)

                if collect:
                    _global_collector.add(
                        exc,
                        context=f"{log_prefix}:{func.__name__}",
                        severity=severity,
                    )

                if reraise:
                    raise

                return default_return

        return wrapper  # type: ignore

    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_prefix: str = "",
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[F], F]:
    """Decorator for automatic retry with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exception types to catch and retry
        log_prefix: Prefix for log messages
        on_retry: Optional callback called before each retry

    Usage:
        @retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        def connect_to_service():
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception: Optional[Exception] = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc

                    if attempt < max_attempts - 1:
                        prefix = f"{log_prefix} " if log_prefix else ""
                        log_warn(
                            f"{prefix}{func.__name__}: Attempt {attempt + 1}/{max_attempts} "
                            f"failed ({exc}), retrying in {current_delay:.1f}s..."
                        )

                        if on_retry:
                            on_retry(exc, attempt + 1)

                        time.sleep(current_delay)
                        current_delay *= backoff

            # All attempts failed
            prefix = f"{log_prefix} " if log_prefix else ""
            log_error(
                f"{prefix}{func.__name__}: All {max_attempts} attempts failed"
            )
            raise last_exception  # type: ignore

        return wrapper  # type: ignore

    return decorator


def safe_call(
    func: Callable[..., T],
    *args: Any,
    default: T = None,  # type: ignore
    log_prefix: str = "",
    **kwargs: Any,
) -> T:
    """Safely call a function, returning default on error.

    Args:
        func: Function to call
        *args: Positional arguments
        default: Default value if function raises
        log_prefix: Prefix for log messages
        **kwargs: Keyword arguments

    Returns:
        Function result or default value

    Usage:
        result = safe_call(risky_function, arg1, arg2, default=[], log_prefix="[IO]")
    """
    try:
        return func(*args, **kwargs)
    except Exception as exc:
        prefix = f"{log_prefix} " if log_prefix else ""
        log_warn(f"{prefix}safe_call({func.__name__}): {exc}")
        return default


# =============================================================================
# Result Type (Optional pattern for error handling)
# =============================================================================

@dataclass
class Result(Generic[T]):
    """Result type for operations that may fail.

    Provides a clean way to return either a value or an error
    without using exceptions for control flow.

    Usage:
        def divide(a: float, b: float) -> Result[float]:
            if b == 0:
                return Result.failure(ValueError("Division by zero"))
            return Result.success(a / b)

        result = divide(10, 2)
        if result.is_success:
            print(f"Result: {result.value}")
        else:
            print(f"Error: {result.error}")
    """
    _value: Optional[T] = None
    _error: Optional[Exception] = None

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        """Create a successful result."""
        return cls(_value=value)

    @classmethod
    def failure(cls, error: Exception) -> "Result[T]":
        """Create a failed result."""
        return cls(_error=error)

    @property
    def is_success(self) -> bool:
        """Check if result is successful."""
        return self._error is None

    @property
    def is_failure(self) -> bool:
        """Check if result is a failure."""
        return self._error is not None

    @property
    def value(self) -> T:
        """Get the value. Raises if result is a failure."""
        if self._error is not None:
            raise self._error
        return self._value  # type: ignore

    @property
    def error(self) -> Optional[Exception]:
        """Get the error if present."""
        return self._error

    def value_or(self, default: T) -> T:
        """Get value or default if failure."""
        if self._error is not None:
            return default
        return self._value  # type: ignore

    def map(self, func: Callable[[T], Any]) -> "Result[Any]":
        """Apply function to value if successful."""
        if self._error is not None:
            return Result.failure(self._error)
        try:
            return Result.success(func(self._value))  # type: ignore
        except Exception as exc:
            return Result.failure(exc)


# =============================================================================
# Utility Functions
# =============================================================================

def format_exception(exc: Exception, include_traceback: bool = False) -> str:
    """Format exception for logging.

    Args:
        exc: Exception to format
        include_traceback: Whether to include full traceback

    Returns:
        Formatted exception string
    """
    exc_type = type(exc).__name__
    message = str(exc)

    if include_traceback:
        tb = traceback.format_exc()
        return f"{exc_type}: {message}\n{tb}"

    return f"{exc_type}: {message}"


def is_recoverable(exc: Exception) -> bool:
    """Check if an exception is recoverable.

    Recoverable errors include:
    - Network/connection errors
    - Temporary resource unavailability
    - Rate limiting

    Non-recoverable errors include:
    - Configuration errors
    - Missing dependencies
    - Permission errors
    """
    non_recoverable = (
        ConfigurationError,
        ImportError,
        PermissionError,
        FileNotFoundError,
        SyntaxError,
        TypeError,
    )
    return not isinstance(exc, non_recoverable)


@contextmanager
def suppress_errors(
    *exceptions: Type[Exception],
    log_prefix: str = "",
    log_level: str = "warn",
) -> Iterator[None]:
    """Context manager to suppress and optionally log errors.

    Args:
        *exceptions: Exception types to suppress (default: Exception)
        log_prefix: Prefix for log messages
        log_level: Log level ("warn", "error", "info")

    Usage:
        with suppress_errors(ValueError, KeyError, log_prefix="[Parse]"):
            value = risky_parse(data)
    """
    if not exceptions:
        exceptions = (Exception,)

    try:
        yield
    except exceptions as exc:
        prefix = f"{log_prefix} " if log_prefix else ""
        message = f"{prefix}Suppressed: {exc}"

        if log_level == "error":
            log_error(message)
        elif log_level == "info":
            log_info(message)
        else:
            log_warn(message)


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Exceptions
    "TranscriptionError",
    "AudioError",
    "AudioCaptureError",
    "AudioProcessingError",
    "ModelError",
    "ModelLoadError",
    "ModelInferenceError",
    "ConfigurationError",
    "CommunicationError",
    "SSEError",
    "VisualizerError",
    "StateError",
    "ResourceError",
    # Enums
    "ErrorSeverity",
    # Classes
    "ErrorRecord",
    "ErrorCollector",
    "ErrorContext",
    "Result",
    # Decorators
    "handle_errors",
    "retry",
    # Functions
    "safe_call",
    "format_exception",
    "is_recoverable",
    "suppress_errors",
    "get_global_collector",
]
