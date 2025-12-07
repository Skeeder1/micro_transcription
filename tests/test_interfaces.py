"""Unit tests for the interfaces and ServiceRegistry."""

import pytest
from unittest.mock import Mock

from shared.interfaces import (
    IBroadcaster,
    IVoiceDetector,
    ITranscriber,
    IAudioCapture,
    ServiceRegistry,
)


class TestIBroadcaster:
    """Test the IBroadcaster protocol."""

    def test_protocol_methods_defined(self):
        """Test that IBroadcaster defines expected methods."""
        assert hasattr(IBroadcaster, "send_preview")
        assert hasattr(IBroadcaster, "send_state")
        assert hasattr(IBroadcaster, "send_vad")
        assert hasattr(IBroadcaster, "send_processing")
        assert hasattr(IBroadcaster, "send_recording")

    def test_implementation_matches_protocol(self):
        """Test that a class can implement IBroadcaster."""
        class MockBroadcaster:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        broadcaster = MockBroadcaster()
        assert isinstance(broadcaster, IBroadcaster)


class TestIVoiceDetector:
    """Test the IVoiceDetector protocol."""

    def test_protocol_methods_defined(self):
        """Test that IVoiceDetector defines expected methods."""
        assert hasattr(IVoiceDetector, "is_speech")
        assert hasattr(IVoiceDetector, "start_calibration")
        assert hasattr(IVoiceDetector, "get_probability")

    def test_implementation_matches_protocol(self):
        """Test that a class can implement IVoiceDetector."""
        import numpy as np

        class MockVoiceDetector:
            def is_speech(self, audio):
                return True

            def get_probability(self, audio):
                return 0.8

            def start_calibration(self):
                pass

            def skip_calibration(self):
                pass

        detector = MockVoiceDetector()
        assert isinstance(detector, IVoiceDetector)


class TestIAudioCapture:
    """Test the IAudioCapture protocol."""

    def test_protocol_methods_defined(self):
        """Test that IAudioCapture defines expected methods."""
        assert hasattr(IAudioCapture, "start")
        assert hasattr(IAudioCapture, "stop")
        assert hasattr(IAudioCapture, "is_recording")
        assert hasattr(IAudioCapture, "set_recording")
        assert hasattr(IAudioCapture, "toggle_recording")

    def test_implementation_matches_protocol(self):
        """Test that a class can implement IAudioCapture."""

        class MockAudioCapture:
            def start(self):
                pass

            def stop(self):
                pass

            def is_recording(self):
                return True

            def set_recording(self, enabled):
                pass

            def toggle_recording(self):
                return True

        capture = MockAudioCapture()
        assert isinstance(capture, IAudioCapture)


class TestITranscriber:
    """Test the ITranscriber protocol."""

    def test_protocol_methods_defined(self):
        """Test that ITranscriber defines expected methods."""
        assert hasattr(ITranscriber, "transcribe")
        assert hasattr(ITranscriber, "is_ready")

    def test_implementation_matches_protocol(self):
        """Test that a class can implement ITranscriber."""
        import numpy as np

        class MockTranscriber:
            def transcribe(self, audio):
                return "transcribed text"

            def is_ready(self):
                return True

        transcriber = MockTranscriber()
        assert isinstance(transcriber, ITranscriber)


class TestServiceRegistry:
    """Test the ServiceRegistry class."""

    def setup_method(self):
        """Clear registry before each test."""
        ServiceRegistry._services.clear()

    def test_register_and_get(self):
        """Test basic register and get."""
        class MockBroadcaster:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        broadcaster = MockBroadcaster()
        ServiceRegistry.register(IBroadcaster, broadcaster)

        result = ServiceRegistry.get(IBroadcaster)
        assert result is broadcaster

    def test_get_unregistered_returns_none(self):
        """Test getting unregistered service returns None."""
        result = ServiceRegistry.get(IBroadcaster)
        assert result is None

    def test_is_registered(self):
        """Test is_registered method."""
        class MockBroadcaster:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        assert not ServiceRegistry.is_registered(IBroadcaster)

        broadcaster = MockBroadcaster()
        ServiceRegistry.register(IBroadcaster, broadcaster)

        assert ServiceRegistry.is_registered(IBroadcaster)

    def test_unregister(self):
        """Test unregistering a service."""
        class MockBroadcaster:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        broadcaster = MockBroadcaster()
        ServiceRegistry.register(IBroadcaster, broadcaster)

        ServiceRegistry.unregister(IBroadcaster)

        assert not ServiceRegistry.is_registered(IBroadcaster)
        assert ServiceRegistry.get(IBroadcaster) is None

    def test_unregister_nonexistent(self):
        """Test unregistering a service that wasn't registered."""
        # Should not raise
        ServiceRegistry.unregister(IBroadcaster)

    def test_clear_all(self):
        """Test clearing all registered services."""
        class MockBroadcaster:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        broadcaster = MockBroadcaster()
        ServiceRegistry.register(IBroadcaster, broadcaster)

        ServiceRegistry.clear_all()

        assert not ServiceRegistry.is_registered(IBroadcaster)

    def test_get_all(self):
        """Test getting all registered services."""
        class MockBroadcaster:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        broadcaster = MockBroadcaster()
        ServiceRegistry.register(IBroadcaster, broadcaster)

        all_services = ServiceRegistry.get_all()

        assert IBroadcaster in all_services
        assert all_services[IBroadcaster] is broadcaster

    def test_override_registration(self):
        """Test that re-registering overrides previous."""
        class MockBroadcaster1:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        class MockBroadcaster2:
            def send_preview(self, ctx, text):
                pass

            def send_state(self, ctx, state):
                pass

            def send_vad(self, ctx, is_voice):
                pass

            def send_processing(self, ctx, is_processing):
                pass

            def send_recording(self, ctx, is_recording):
                pass

        broadcaster1 = MockBroadcaster1()
        broadcaster2 = MockBroadcaster2()

        ServiceRegistry.register(IBroadcaster, broadcaster1)
        ServiceRegistry.register(IBroadcaster, broadcaster2)

        result = ServiceRegistry.get(IBroadcaster)
        assert result is broadcaster2
