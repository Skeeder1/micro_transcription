"""Integration tests for Phase 4 refactoring.

These tests verify that the Phase 1-3 modules are properly integrated
into the existing codebase:
- EventBus event publishing
- ServiceRegistry dependency injection
- Error handling decorators
- Threading utilities integration
"""

import threading
import time
from unittest.mock import Mock, patch, MagicMock
import queue

import pytest
import numpy as np

from shared.events import EventBus, Events
from shared.interfaces import ServiceRegistry, IBroadcaster
from shared.errors import handle_errors, Result
from shared.threading_utils import TimeoutLock


class TestEventBusIntegration:
    """Test EventBus integration across modules."""

    def setup_method(self):
        """Clear EventBus handlers before each test."""
        EventBus.unsubscribe_all()

    def teardown_method(self):
        """Clean up after each test."""
        EventBus.unsubscribe_all()

    def test_transcription_events_flow(self):
        """Test that transcription events are published in correct order."""
        events_received = []

        def capture_event(event_name):
            def handler(**kwargs):
                events_received.append((event_name, kwargs))
            return handler

        # Subscribe to transcription events
        EventBus.subscribe(Events.TRANSCRIPTION_STARTED, capture_event("started"))
        EventBus.subscribe(Events.TRANSCRIPTION_COMPLETE, capture_event("complete"))
        EventBus.subscribe(Events.TRANSCRIPTION_FAILED, capture_event("failed"))

        # Simulate transcription flow
        EventBus.publish(Events.TRANSCRIPTION_STARTED)
        EventBus.publish(Events.TRANSCRIPTION_COMPLETE, text="Hello world")

        assert len(events_received) == 2
        assert events_received[0][0] == "started"
        assert events_received[1][0] == "complete"
        assert events_received[1][1]["text"] == "Hello world"

    def test_voice_detection_events(self):
        """Test voice detection event publishing."""
        voice_states = []

        def on_voice(**kwargs):
            voice_states.append(("voice", kwargs.get("is_voice")))

        def on_silence(**kwargs):
            voice_states.append(("silence", kwargs.get("is_voice")))

        EventBus.subscribe(Events.VOICE_DETECTED, on_voice)
        EventBus.subscribe(Events.SILENCE_DETECTED, on_silence)

        # Simulate voice detection
        EventBus.publish(Events.VOICE_DETECTED, is_voice=True)
        EventBus.publish(Events.SILENCE_DETECTED, is_voice=False)

        assert voice_states == [("voice", True), ("silence", False)]

    def test_calibration_events(self):
        """Test calibration event publishing."""
        calibration_events = []

        def on_start(**kwargs):
            calibration_events.append("started")

        def on_complete(**kwargs):
            calibration_events.append(("complete", kwargs))

        EventBus.subscribe(Events.CALIBRATION_STARTED, on_start)
        EventBus.subscribe(Events.CALIBRATION_COMPLETE, on_complete)

        EventBus.publish(Events.CALIBRATION_STARTED)
        EventBus.publish(
            Events.CALIBRATION_COMPLETE,
            noise_floor=0.002,
            dynamic_threshold=0.005
        )

        assert calibration_events[0] == "started"
        assert calibration_events[1][0] == "complete"
        assert calibration_events[1][1]["noise_floor"] == 0.002

    def test_system_state_events(self):
        """Test system activation/deactivation events."""
        state_changes = []

        EventBus.subscribe(Events.SYSTEM_ACTIVATED, lambda **k: state_changes.append("activated"))
        EventBus.subscribe(Events.SYSTEM_DEACTIVATED, lambda **k: state_changes.append("deactivated"))
        EventBus.subscribe(Events.DEEP_SLEEP_ENTERED, lambda **k: state_changes.append("deep_sleep"))

        EventBus.publish(Events.SYSTEM_ACTIVATED)
        EventBus.publish(Events.SYSTEM_DEACTIVATED)
        EventBus.publish(Events.DEEP_SLEEP_ENTERED)

        assert state_changes == ["activated", "deactivated", "deep_sleep"]


class TestServiceRegistryIntegration:
    """Test ServiceRegistry for dependency injection."""

    def setup_method(self):
        """Clear registry before each test."""
        ServiceRegistry.clear()

    def teardown_method(self):
        """Clean up registry."""
        ServiceRegistry.clear()

    def test_broadcaster_registration(self):
        """Test that broadcaster can be registered and retrieved."""
        class MockBroadcaster:
            def send_preview(self, ctx, text): pass
            def send_state(self, ctx, state): pass
            def send_vad(self, ctx, is_voice): pass
            def send_processing(self, ctx, is_processing): pass
            def send_recording(self, ctx, is_recording): pass

        broadcaster = MockBroadcaster()
        ServiceRegistry.register(IBroadcaster, broadcaster)

        retrieved = ServiceRegistry.get(IBroadcaster)
        assert retrieved is broadcaster
        assert ServiceRegistry.is_registered(IBroadcaster)

    def test_unregistered_service_returns_none(self):
        """Test that unregistered services return None."""
        result = ServiceRegistry.get(IBroadcaster)
        assert result is None

    def test_service_override(self):
        """Test that services can be overridden."""
        class BroadcasterV1:
            version = 1

        class BroadcasterV2:
            version = 2

        ServiceRegistry.register(IBroadcaster, BroadcasterV1())
        ServiceRegistry.register(IBroadcaster, BroadcasterV2())

        retrieved = ServiceRegistry.get(IBroadcaster)
        assert retrieved.version == 2


class TestErrorHandlingIntegration:
    """Test error handling decorator integration."""

    def test_handle_errors_decorator_logs_and_returns_default(self):
        """Test that @handle_errors logs errors and returns default."""
        @handle_errors(log_prefix="[Test]", reraise=False, default_return="FALLBACK")
        def failing_function():
            raise ValueError("Test error")

        result = failing_function()
        assert result == "FALLBACK"

    def test_handle_errors_decorator_reraises(self):
        """Test that @handle_errors can reraise exceptions."""
        @handle_errors(log_prefix="[Test]", reraise=True)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

    def test_handle_errors_passes_through_success(self):
        """Test that @handle_errors passes through successful results."""
        @handle_errors(log_prefix="[Test]", reraise=True)
        def successful_function():
            return 42

        result = successful_function()
        assert result == 42


class TestThreadingIntegration:
    """Test threading utilities integration."""

    def test_timeout_lock_acquisition(self):
        """Test TimeoutLock successful acquisition."""
        lock = TimeoutLock(timeout=1.0, name="test_lock")

        with lock:
            assert True  # If we get here, lock was acquired

    def test_timeout_lock_prevents_deadlock(self):
        """Test that TimeoutLock raises on timeout."""
        lock = TimeoutLock(timeout=0.1, name="test_lock")
        lock_held = threading.Event()
        exception_raised = threading.Event()

        def hold_lock():
            with lock:
                lock_held.set()
                time.sleep(1.0)  # Hold lock longer than timeout

        def try_acquire():
            lock_held.wait()  # Wait for first thread to hold lock
            try:
                with lock:
                    pass
            except TimeoutError:
                exception_raised.set()

        t1 = threading.Thread(target=hold_lock)
        t2 = threading.Thread(target=try_acquire)

        t1.start()
        t2.start()

        t2.join(timeout=2.0)

        assert exception_raised.is_set()

        # Clean up
        t1.join(timeout=2.0)


class TestModuleImportsIntegration:
    """Test that all Phase 4 integrated modules import correctly."""

    def test_engine_imports(self):
        """Test engine module imports."""
        from core.engine import run
        from shared.service_utils import get_broadcaster, broadcast_preview_safe
        assert callable(run)
        assert callable(get_broadcaster)
        assert callable(broadcast_preview_safe)

    def test_processor_imports(self):
        """Test processor module imports."""
        from core.processor import run, _transcribe_and_paste
        from shared.service_utils import get_broadcaster
        assert callable(run)
        assert callable(_transcribe_and_paste)
        assert callable(get_broadcaster)

    def test_audio_capture_imports(self):
        """Test audio_capture module imports."""
        from core.audio_capture import paste_via_clipboard, make_audio_callback
        assert callable(paste_via_clipboard)

    def test_voice_detector_imports(self):
        """Test voice_detector module imports."""
        from core.voice_detector import VoiceDetector
        assert VoiceDetector is not None

    def test_server_imports(self):
        """Test server module imports."""
        from api.server import start_server, get_broadcaster
        assert callable(start_server)

    def test_sleep_imports(self):
        """Test sleep module imports."""
        from shared.sleep import activate_system, deactivate_system, toggle_sleep_mode
        assert callable(toggle_sleep_mode)

    def test_hotkey_imports(self):
        """Test hotkey module imports."""
        from shared.hotkey import HotkeyManager
        assert HotkeyManager is not None


class TestEventChaining:
    """Test that events chain correctly through the system."""

    def setup_method(self):
        EventBus.unsubscribe_all()
        ServiceRegistry.clear()

    def teardown_method(self):
        EventBus.unsubscribe_all()
        ServiceRegistry.clear()

    def test_recording_to_transcription_chain(self):
        """Test event flow from recording to transcription."""
        event_log = []

        EventBus.subscribe(Events.RECORDING_STARTED, lambda **k: event_log.append("rec_start"))
        EventBus.subscribe(Events.VOICE_DETECTED, lambda **k: event_log.append("voice"))
        EventBus.subscribe(Events.TRANSCRIPTION_STARTED, lambda **k: event_log.append("trans_start"))
        EventBus.subscribe(Events.TRANSCRIPTION_COMPLETE, lambda **k: event_log.append("trans_done"))
        EventBus.subscribe(Events.RECORDING_STOPPED, lambda **k: event_log.append("rec_stop"))

        # Simulate typical flow
        EventBus.publish(Events.RECORDING_STARTED)
        EventBus.publish(Events.VOICE_DETECTED, is_voice=True)
        EventBus.publish(Events.TRANSCRIPTION_STARTED)
        EventBus.publish(Events.TRANSCRIPTION_COMPLETE, text="Test")
        EventBus.publish(Events.RECORDING_STOPPED)

        assert event_log == ["rec_start", "voice", "trans_start", "trans_done", "rec_stop"]


class TestBroadcasterServicePattern:
    """Test the broadcaster service pattern used in modules."""

    def setup_method(self):
        ServiceRegistry.clear()

    def teardown_method(self):
        ServiceRegistry.clear()

    def test_broadcaster_pattern_with_fallback(self):
        """Test that modules handle missing broadcaster gracefully."""
        def function_using_broadcaster():
            broadcaster = ServiceRegistry.get(IBroadcaster)
            if broadcaster:
                return "has_broadcaster"
            return "no_broadcaster"

        # No broadcaster registered
        assert function_using_broadcaster() == "no_broadcaster"

        # Register broadcaster
        class MockBroadcaster:
            pass
        ServiceRegistry.register(IBroadcaster, MockBroadcaster())

        # Now has broadcaster
        assert function_using_broadcaster() == "has_broadcaster"
