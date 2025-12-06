"""
Tests for F8/F9 logic and system startup behavior.

Run with: .venv/bin/python -m pytest tests/test_f8_f9_logic.py -v
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from shared.context import AppContext, SleepContext, AudioContext


class TestDefaultStates:
    """Test that the system starts with the correct default states."""

    def test_system_starts_active(self):
        """System should start ACTIVE (not sleeping)."""
        ctx = AppContext()
        assert ctx.is_sleeping is False, "System should start active (is_sleeping=False)"

    def test_recording_starts_on(self):
        """Recording should be ON by default."""
        ctx = AppContext()
        assert ctx.is_recording is True, "Recording should start ON (is_recording=True)"

    def test_not_deep_sleeping_at_start(self):
        """Should not be in deep sleep at start."""
        ctx = AppContext()
        assert ctx.is_deep_sleeping is False

    def test_sleep_start_time_is_zero_at_start(self):
        """sleep_start_time should be 0 when not sleeping."""
        ctx = AppContext()
        assert ctx.sleep_start_time == 0.0

    def test_last_speech_time_initialized_to_now(self):
        """last_speech_time should be initialized to current time."""
        before = time.time()
        ctx = AppContext()
        after = time.time()
        assert before <= ctx.last_speech_time <= after


class TestSleepContext:
    """Test SleepContext dataclass defaults."""

    def test_sleep_context_defaults(self):
        """SleepContext should have correct defaults."""
        sleep_ctx = SleepContext()
        assert sleep_ctx.is_sleeping is False
        assert sleep_ctx.is_deep_sleeping is False
        assert sleep_ctx.sleep_start_time == 0.0


class TestAudioContext:
    """Test AudioContext dataclass defaults."""

    def test_audio_context_defaults(self):
        """AudioContext should have correct defaults."""
        audio_ctx = AudioContext()
        assert audio_ctx.is_recording is True
        assert audio_ctx.force_flush is False
        assert audio_ctx.is_processing is False
        assert audio_ctx.vad_detecting is False


class TestToggleRecording:
    """Test F8 toggle_recording behavior."""

    def test_toggle_recording_when_system_sleeping(self):
        """F8 should be ignored when system is sleeping."""
        from shared.sleep import toggle_recording

        ctx = AppContext()
        ctx.is_sleeping = True
        ctx.is_recording = False

        result = toggle_recording(ctx)

        # Should return False and not change state
        assert result is False
        assert ctx.is_recording is False

    @patch('api.server.broadcast_recording')
    @patch('api.server.broadcast_preview')
    def test_toggle_recording_activates_mic(self, mock_preview, mock_recording):
        """F8 should toggle mic ON when system is active and mic is OFF."""
        from shared.sleep import toggle_recording

        ctx = AppContext()
        ctx.is_sleeping = False
        ctx.audio.set_recording(False)

        result = toggle_recording(ctx)

        assert result is True
        assert ctx.is_recording is True

    @patch('api.server.broadcast_recording')
    @patch('api.server.broadcast_preview')
    def test_toggle_recording_deactivates_mic_and_sets_force_flush(self, mock_preview, mock_recording):
        """F8 should toggle mic OFF and set force_flush when mic is ON."""
        from shared.sleep import toggle_recording

        ctx = AppContext()
        ctx.is_sleeping = False
        ctx.audio.set_recording(True)

        result = toggle_recording(ctx)

        assert result is False
        assert ctx.is_recording is False
        assert ctx.force_flush is True


class TestToggleSystem:
    """Test F9 toggle_system behavior."""

    @patch('ui.manager.start_visualizer')
    @patch('api.server.broadcast_state')
    @patch('api.server.broadcast_recording')
    @patch('api.server.broadcast_preview')
    def test_activate_system_from_sleep(self, mock_preview, mock_recording, mock_state, mock_vis):
        """F9 should activate system when sleeping."""
        from shared.sleep import activate_system

        ctx = AppContext()
        ctx.is_sleeping = True
        ctx.is_recording = False

        activate_system(ctx)

        assert ctx.is_sleeping is False
        assert ctx.is_recording is True
        mock_vis.assert_called_once()

    @patch('ui.manager.stop_visualizer')
    @patch('api.server.broadcast_state')
    @patch('api.server.broadcast_recording')
    @patch('api.server.broadcast_preview')
    def test_deactivate_system_from_active(self, mock_preview, mock_recording, mock_state, mock_vis):
        """F9 should deactivate system when active."""
        from shared.sleep import deactivate_system

        ctx = AppContext()
        ctx.is_sleeping = False
        ctx.is_recording = True

        deactivate_system(ctx)

        assert ctx.is_sleeping is True
        assert ctx.is_recording is False
        mock_vis.assert_called_once()


class TestAutoSleep:
    """Test auto-sleep functionality."""

    @patch('shared.sleep.deactivate_system')
    def test_auto_sleep_after_silence(self, mock_deactivate):
        """System should auto-sleep after configured silence duration."""
        from shared.sleep import check_auto_sleep
        from shared import config

        ctx = AppContext()
        ctx.is_sleeping = False
        ctx.is_recording = True
        # Set last_speech_time to long ago
        ctx.last_speech_time = time.time() - config.AUTO_SLEEP_SECONDS - 10

        check_auto_sleep(ctx)

        mock_deactivate.assert_called_once()

    @patch('shared.sleep.deactivate_system')
    def test_no_auto_sleep_when_speaking(self, mock_deactivate):
        """System should not auto-sleep if speech was recent."""
        from shared.sleep import check_auto_sleep

        ctx = AppContext()
        ctx.is_sleeping = False
        ctx.is_recording = True
        ctx.last_speech_time = time.time()  # Just now

        check_auto_sleep(ctx)

        mock_deactivate.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
