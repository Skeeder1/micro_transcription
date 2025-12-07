"""Unit tests for the EventBus system."""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from shared.events import EventBus, Events, _EventBus


class TestEvents:
    """Test the Events enumeration."""

    def test_events_enum_exists(self):
        """Test that Events enum is defined."""
        assert Events is not None

    def test_system_events_exist(self):
        """Test that system events are defined."""
        assert hasattr(Events, "SYSTEM_ACTIVATED")
        assert hasattr(Events, "SYSTEM_DEACTIVATED")

    def test_recording_events_exist(self):
        """Test that recording events are defined."""
        assert hasattr(Events, "RECORDING_STARTED")
        assert hasattr(Events, "RECORDING_STOPPED")

    def test_transcription_events_exist(self):
        """Test that transcription events are defined."""
        assert hasattr(Events, "TRANSCRIPTION_STARTED")
        assert hasattr(Events, "TRANSCRIPTION_COMPLETE")

    def test_voice_detection_events_exist(self):
        """Test that voice detection events are defined."""
        assert hasattr(Events, "VOICE_DETECTED")
        assert hasattr(Events, "SILENCE_DETECTED")

    def test_events_are_unique(self):
        """Test that all events have unique values."""
        values = [e.value for e in Events]
        assert len(values) == len(set(values))


class TestEventBus:
    """Test the EventBus class."""

    def setup_method(self):
        """Create a fresh EventBus for each test."""
        self.bus = _EventBus()

    def test_subscribe_and_publish(self):
        """Test basic subscribe and publish."""
        handler = Mock()
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler)

        self.bus.publish(Events.SYSTEM_ACTIVATED)

        handler.assert_called_once()

    def test_publish_with_kwargs(self):
        """Test publish passes kwargs to handlers."""
        handler = Mock()
        self.bus.subscribe(Events.TRANSCRIPTION_COMPLETE, handler)

        self.bus.publish(Events.TRANSCRIPTION_COMPLETE, text="Hello")

        handler.assert_called_once_with(text="Hello")

    def test_multiple_handlers(self):
        """Test multiple handlers for same event."""
        handler1 = Mock()
        handler2 = Mock()
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler1)
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler2)

        self.bus.publish(Events.SYSTEM_ACTIVATED)

        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_unsubscribe(self):
        """Test unsubscribing a handler."""
        handler = Mock()
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler)
        self.bus.unsubscribe(Events.SYSTEM_ACTIVATED, handler)

        self.bus.publish(Events.SYSTEM_ACTIVATED)

        handler.assert_not_called()

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a handler that wasn't subscribed."""
        handler = Mock()
        # Should not raise
        self.bus.unsubscribe(Events.SYSTEM_ACTIVATED, handler)

    def test_publish_to_no_handlers(self):
        """Test publishing event with no handlers."""
        # Should not raise
        self.bus.publish(Events.SYSTEM_ACTIVATED)

    def test_handler_exception_doesnt_break_others(self):
        """Test that exception in one handler doesn't break others."""
        handler1 = Mock(side_effect=Exception("Error"))
        handler2 = Mock()

        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler1)
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler2)

        # Should not raise
        self.bus.publish(Events.SYSTEM_ACTIVATED)

        handler1.assert_called_once()
        handler2.assert_called_once()

    def test_unsubscribe_all_for_event(self):
        """Test clearing all handlers for an event."""
        handler1 = Mock()
        handler2 = Mock()
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler1)
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler2)

        self.bus.unsubscribe_all(Events.SYSTEM_ACTIVATED)
        self.bus.publish(Events.SYSTEM_ACTIVATED)

        handler1.assert_not_called()
        handler2.assert_not_called()

    def test_unsubscribe_all_handlers(self):
        """Test clearing all handlers."""
        handler1 = Mock()
        handler2 = Mock()
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler1)
        self.bus.subscribe(Events.TRANSCRIPTION_COMPLETE, handler2)

        self.bus.unsubscribe_all()
        self.bus.publish(Events.SYSTEM_ACTIVATED)
        self.bus.publish(Events.TRANSCRIPTION_COMPLETE)

        handler1.assert_not_called()
        handler2.assert_not_called()

    def test_get_handler_count(self):
        """Test getting handler count."""
        handler1 = Mock()
        handler2 = Mock()

        assert self.bus.get_handler_count(Events.SYSTEM_ACTIVATED) == 0

        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler1)
        assert self.bus.get_handler_count(Events.SYSTEM_ACTIVATED) == 1

        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler2)
        assert self.bus.get_handler_count(Events.SYSTEM_ACTIVATED) == 2

    def test_publish_async(self):
        """Test async publish returns a thread."""
        handler = Mock()
        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler)

        thread = self.bus.publish_async(Events.SYSTEM_ACTIVATED)

        assert isinstance(thread, threading.Thread)
        thread.join(timeout=1.0)
        handler.assert_called_once()

    def test_thread_safety(self):
        """Test EventBus is thread-safe."""
        results = []
        lock = threading.Lock()

        def handler(**kwargs):
            with lock:
                results.append(threading.current_thread().name)

        self.bus.subscribe(Events.SYSTEM_ACTIVATED, handler)

        threads = []
        for i in range(10):
            t = threading.Thread(
                target=lambda: self.bus.publish(Events.SYSTEM_ACTIVATED)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(results) == 10


class TestGlobalEventBus:
    """Test the global EventBus singleton."""

    def test_global_eventbus_exists(self):
        """Test that global EventBus is accessible."""
        from shared.events import EventBus
        assert EventBus is not None

    def test_global_eventbus_is_singleton(self):
        """Test that EventBus is the same instance."""
        from shared.events import EventBus as Bus1
        from shared.events import EventBus as Bus2
        assert Bus1 is Bus2
