"""Unit tests for the centralized error handling system."""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from shared.errors import (
    # Exceptions
    TranscriptionError,
    AudioError,
    AudioCaptureError,
    AudioProcessingError,
    ModelError,
    ModelLoadError,
    ModelInferenceError,
    ConfigurationError,
    CommunicationError,
    SSEError,
    VisualizerError,
    StateError,
    ResourceError,
    # Enums
    ErrorSeverity,
    # Classes
    ErrorRecord,
    ErrorCollector,
    ErrorContext,
    Result,
    # Decorators
    handle_errors,
    retry,
    # Functions
    safe_call,
    format_exception,
    is_recoverable,
    suppress_errors,
    get_global_collector,
)


class TestExceptionHierarchy:
    """Test the custom exception hierarchy."""

    def test_transcription_error_is_base(self):
        """Test that TranscriptionError is the base class."""
        assert issubclass(AudioError, TranscriptionError)
        assert issubclass(ModelError, TranscriptionError)
        assert issubclass(ConfigurationError, TranscriptionError)
        assert issubclass(CommunicationError, TranscriptionError)
        assert issubclass(StateError, TranscriptionError)
        assert issubclass(ResourceError, TranscriptionError)

    def test_audio_errors_hierarchy(self):
        """Test audio error hierarchy."""
        assert issubclass(AudioCaptureError, AudioError)
        assert issubclass(AudioProcessingError, AudioError)

    def test_model_errors_hierarchy(self):
        """Test model error hierarchy."""
        assert issubclass(ModelLoadError, ModelError)
        assert issubclass(ModelInferenceError, ModelError)

    def test_communication_errors_hierarchy(self):
        """Test communication error hierarchy."""
        assert issubclass(SSEError, CommunicationError)
        assert issubclass(VisualizerError, CommunicationError)

    def test_exception_with_cause(self):
        """Test exception with cause chain."""
        cause = ValueError("Original error")
        error = TranscriptionError("Wrapped error", cause=cause)

        assert error.cause is cause
        assert "caused by" in str(error)

    def test_exception_without_cause(self):
        """Test exception without cause."""
        error = TranscriptionError("Simple error")

        assert error.cause is None
        assert error.message == "Simple error"

    def test_exception_has_timestamp(self):
        """Test exception records timestamp."""
        error = TranscriptionError("Error")
        assert error.timestamp is not None


class TestErrorSeverity:
    """Test the ErrorSeverity enum."""

    def test_severity_levels_exist(self):
        """Test that all severity levels are defined."""
        assert hasattr(ErrorSeverity, "DEBUG")
        assert hasattr(ErrorSeverity, "INFO")
        assert hasattr(ErrorSeverity, "WARNING")
        assert hasattr(ErrorSeverity, "ERROR")
        assert hasattr(ErrorSeverity, "CRITICAL")

    def test_severity_ordering(self):
        """Test that severity levels can be compared."""
        assert ErrorSeverity.DEBUG.value < ErrorSeverity.INFO.value
        assert ErrorSeverity.INFO.value < ErrorSeverity.WARNING.value
        assert ErrorSeverity.WARNING.value < ErrorSeverity.ERROR.value
        assert ErrorSeverity.ERROR.value < ErrorSeverity.CRITICAL.value


class TestErrorRecord:
    """Test the ErrorRecord class."""

    def test_record_creation(self):
        """Test creating an error record."""
        exc = ValueError("Test error")
        record = ErrorRecord(exception=exc, context="test_context")

        assert record.exception is exc
        assert record.context == "test_context"
        assert record.severity == ErrorSeverity.ERROR
        assert record.timestamp is not None
        assert record.thread_name is not None

    def test_record_to_dict(self):
        """Test converting record to dictionary."""
        exc = ValueError("Test error")
        record = ErrorRecord(exception=exc, context="test")

        d = record.to_dict()

        assert d["exception_type"] == "ValueError"
        assert d["message"] == "Test error"
        assert d["context"] == "test"
        assert "timestamp" in d


class TestErrorCollector:
    """Test the ErrorCollector class."""

    def test_add_error(self):
        """Test adding an error."""
        collector = ErrorCollector()
        exc = ValueError("Test")

        collector.add(exc, context="test")

        assert collector.error_count == 1
        assert collector.has_errors

    def test_max_errors_limit(self):
        """Test that collector respects max_errors limit."""
        collector = ErrorCollector(max_errors=3)

        for i in range(5):
            collector.add(ValueError(f"Error {i}"))

        assert collector.error_count == 3

    def test_get_errors_filtered_by_severity(self):
        """Test filtering errors by severity."""
        collector = ErrorCollector()
        collector.add(ValueError("Warn"), severity=ErrorSeverity.WARNING)
        collector.add(ValueError("Error"), severity=ErrorSeverity.ERROR)

        warnings = collector.get_errors(severity=ErrorSeverity.WARNING)
        errors = collector.get_errors(severity=ErrorSeverity.ERROR)

        assert len(warnings) == 1
        assert len(errors) == 1

    def test_get_errors_filtered_by_context(self):
        """Test filtering errors by context."""
        collector = ErrorCollector()
        collector.add(ValueError("1"), context="audio")
        collector.add(ValueError("2"), context="model")
        collector.add(ValueError("3"), context="audio")

        audio_errors = collector.get_errors(context="audio")

        assert len(audio_errors) == 2

    def test_clear(self):
        """Test clearing errors."""
        collector = ErrorCollector()
        collector.add(ValueError("Test"))

        collector.clear()

        assert not collector.has_errors
        assert collector.error_count == 0

    def test_get_summary(self):
        """Test getting error summary."""
        collector = ErrorCollector()
        collector.add(ValueError("1"), severity=ErrorSeverity.WARNING)
        collector.add(ValueError("2"), severity=ErrorSeverity.ERROR)
        collector.add(ValueError("3"), severity=ErrorSeverity.ERROR)

        summary = collector.get_summary()

        assert "WARNING" in summary
        assert "ERROR" in summary

    def test_thread_safety(self):
        """Test collector is thread-safe."""
        collector = ErrorCollector(max_errors=100)

        def add_errors():
            for i in range(10):
                collector.add(ValueError(f"Thread error {i}"))

        threads = [threading.Thread(target=add_errors) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert collector.error_count == 50


class TestErrorContext:
    """Test the ErrorContext context manager."""

    def test_context_captures_exception(self):
        """Test that context captures exceptions."""
        ctx = ErrorContext("test", suppress_exceptions=True, log_on_exit=False)

        with ctx:
            raise ValueError("Test error")

        assert ctx.has_errors
        assert len(ctx.errors) == 1

    def test_context_suppress_exceptions(self):
        """Test suppressing exceptions."""
        ctx = ErrorContext("test", suppress_exceptions=True, log_on_exit=False)

        with ctx:
            raise ValueError("Test")

        # Should not raise

    def test_context_reraise_exceptions(self):
        """Test not suppressing exceptions."""
        ctx = ErrorContext("test", suppress_exceptions=False, log_on_exit=False)

        with pytest.raises(ValueError):
            with ctx:
                raise ValueError("Test")


class TestHandleErrorsDecorator:
    """Test the handle_errors decorator."""

    def test_decorator_catches_exception(self):
        """Test decorator catches exceptions."""

        @handle_errors(reraise=False, default_return="default")
        def failing_func():
            raise ValueError("Test")

        result = failing_func()
        assert result == "default"

    def test_decorator_reraises_exception(self):
        """Test decorator can reraise exceptions."""

        @handle_errors(reraise=True)
        def failing_func():
            raise ValueError("Test")

        with pytest.raises(ValueError):
            failing_func()

    def test_decorator_only_catches_specified_exceptions(self):
        """Test decorator only catches specified exceptions."""

        @handle_errors(reraise=False, default_return="default", exceptions=(ValueError,))
        def failing_func():
            raise TypeError("Test")

        with pytest.raises(TypeError):
            failing_func()

    def test_decorator_passes_through_success(self):
        """Test decorator passes through successful results."""

        @handle_errors()
        def success_func():
            return "success"

        result = success_func()
        assert result == "success"


class TestRetryDecorator:
    """Test the retry decorator."""

    def test_retry_succeeds_on_first_try(self):
        """Test retry with immediate success."""
        call_count = [0]

        @retry(max_attempts=3, delay=0.01)
        def success_func():
            call_count[0] += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count[0] == 1

    def test_retry_succeeds_after_failures(self):
        """Test retry succeeds after initial failures."""
        call_count = [0]

        @retry(max_attempts=3, delay=0.01)
        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Not ready yet")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count[0] == 3

    def test_retry_fails_after_max_attempts(self):
        """Test retry raises after max attempts."""
        call_count = [0]

        @retry(max_attempts=3, delay=0.01)
        def always_fails():
            call_count[0] += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fails()

        assert call_count[0] == 3

    def test_retry_only_retries_specified_exceptions(self):
        """Test retry only retries specified exceptions."""
        call_count = [0]

        @retry(max_attempts=3, delay=0.01, exceptions=(ValueError,))
        def wrong_exception():
            call_count[0] += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            wrong_exception()

        assert call_count[0] == 1

    def test_retry_calls_on_retry_callback(self):
        """Test retry calls on_retry callback."""
        callback_calls = []

        def on_retry(exc, attempt):
            callback_calls.append((str(exc), attempt))

        @retry(max_attempts=3, delay=0.01, on_retry=on_retry)
        def flaky_func():
            if len(callback_calls) < 2:
                raise ValueError("Not ready")
            return "success"

        flaky_func()

        assert len(callback_calls) == 2


class TestSafeCall:
    """Test the safe_call function."""

    def test_safe_call_success(self):
        """Test safe_call with successful function."""

        def success():
            return "result"

        result = safe_call(success)
        assert result == "result"

    def test_safe_call_failure_returns_default(self):
        """Test safe_call returns default on failure."""

        def failure():
            raise ValueError("Error")

        result = safe_call(failure, default="default")
        assert result == "default"

    def test_safe_call_with_args(self):
        """Test safe_call passes arguments."""

        def add(a, b):
            return a + b

        result = safe_call(add, 1, 2)
        assert result == 3


class TestResult:
    """Test the Result type."""

    def test_success_result(self):
        """Test creating a success result."""
        result = Result.success(42)

        assert result.is_success
        assert not result.is_failure
        assert result.value == 42
        assert result.error is None

    def test_failure_result(self):
        """Test creating a failure result."""
        exc = ValueError("Error")
        result = Result.failure(exc)

        assert not result.is_success
        assert result.is_failure
        assert result.error is exc

    def test_value_raises_on_failure(self):
        """Test accessing value on failure raises."""
        result = Result.failure(ValueError("Error"))

        with pytest.raises(ValueError):
            _ = result.value

    def test_value_or_returns_default_on_failure(self):
        """Test value_or returns default on failure."""
        result = Result.failure(ValueError("Error"))

        assert result.value_or("default") == "default"

    def test_value_or_returns_value_on_success(self):
        """Test value_or returns value on success."""
        result = Result.success(42)

        assert result.value_or(0) == 42

    def test_map_on_success(self):
        """Test map on success result."""
        result = Result.success(5)
        mapped = result.map(lambda x: x * 2)

        assert mapped.is_success
        assert mapped.value == 10

    def test_map_on_failure(self):
        """Test map on failure result."""
        exc = ValueError("Error")
        result = Result.failure(exc)
        mapped = result.map(lambda x: x * 2)

        assert mapped.is_failure
        assert mapped.error is exc

    def test_map_catches_exceptions(self):
        """Test map catches exceptions in mapper."""
        result = Result.success(5)
        mapped = result.map(lambda x: x / 0)

        assert mapped.is_failure
        assert isinstance(mapped.error, ZeroDivisionError)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_exception_simple(self):
        """Test simple exception formatting."""
        exc = ValueError("Test message")
        formatted = format_exception(exc)

        assert "ValueError" in formatted
        assert "Test message" in formatted

    def test_is_recoverable_true(self):
        """Test recoverable exceptions."""
        assert is_recoverable(ConnectionError())
        assert is_recoverable(TimeoutError())
        assert is_recoverable(ValueError())

    def test_is_recoverable_false(self):
        """Test non-recoverable exceptions."""
        assert not is_recoverable(ConfigurationError("Config error"))
        assert not is_recoverable(ImportError())
        assert not is_recoverable(PermissionError())

    def test_suppress_errors_context(self):
        """Test suppress_errors context manager."""
        value = None

        with suppress_errors(ValueError, log_prefix="[Test]"):
            raise ValueError("Suppressed")
            value = "never reached"

        assert value is None  # Exception was suppressed
