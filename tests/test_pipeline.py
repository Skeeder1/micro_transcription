"""Tests for audio pipeline components."""

import numpy as np
import pytest
import time

from core.pipeline import AudioBuffer, PreviewManager, ProductionManager


class TestAudioBuffer:
    """Tests for AudioBuffer class."""

    @pytest.fixture
    def buffer(self):
        """Create buffer with known settings."""
        return AudioBuffer(
            max_production_seconds=5.0,
            preview_window_seconds=2.0,
            block_seconds=0.5,
        )

    @pytest.fixture
    def audio_block(self):
        """Create sample audio block."""
        return np.random.randn(8000).astype(np.float32)

    def test_initialization(self, buffer):
        """Test buffer initializes with correct limits."""
        assert buffer.max_production_blocks == 10  # 5s / 0.5s
        assert buffer.max_preview_blocks == 4      # 2s / 0.5s
        assert not buffer.has_production_audio
        assert not buffer.has_preview_audio

    def test_add_voice_audio(self, buffer, audio_block):
        """Test adding voice audio to buffer."""
        buffer.add_voice_audio(audio_block)

        assert buffer.has_production_audio
        assert buffer.has_preview_audio
        assert buffer.silence_blocks == 0

    def test_add_silence(self, buffer):
        """Test adding silence increments counter."""
        buffer.add_silence()
        assert buffer.silence_blocks == 1

        buffer.add_silence()
        assert buffer.silence_blocks == 2

    def test_voice_resets_silence(self, buffer, audio_block):
        """Test that voice audio resets silence counter."""
        buffer.add_silence()
        buffer.add_silence()
        assert buffer.silence_blocks == 2

        buffer.add_voice_audio(audio_block)
        assert buffer.silence_blocks == 0

    def test_clear_all(self, buffer, audio_block):
        """Test clearing both buffers."""
        buffer.add_voice_audio(audio_block)
        buffer.add_silence()

        buffer.clear()

        assert not buffer.has_production_audio
        assert not buffer.has_preview_audio
        assert buffer.silence_blocks == 0

    def test_preview_window_sliding(self, buffer, audio_block):
        """Test preview window slides (oldest removed)."""
        # Add more blocks than preview window allows
        for _ in range(6):
            buffer.add_voice_audio(audio_block)

        # Preview should be limited to max_preview_blocks
        preview = buffer.get_preview_audio()
        expected_samples = buffer.max_preview_blocks * len(audio_block)
        assert len(preview) == expected_samples

    def test_production_overflow_detection(self, buffer, audio_block):
        """Test production overflow detection."""
        assert not buffer.is_production_overflow

        # Fill up to limit
        for _ in range(buffer.max_production_blocks):
            buffer.add_voice_audio(audio_block)

        assert buffer.is_production_overflow

    def test_get_production_audio_concatenation(self, buffer, audio_block):
        """Test production audio is concatenated correctly."""
        buffer.add_voice_audio(audio_block)
        buffer.add_voice_audio(audio_block)

        audio = buffer.get_production_audio()
        assert len(audio) == 2 * len(audio_block)

    def test_get_empty_production_returns_none(self, buffer):
        """Test empty buffer returns None."""
        assert buffer.get_production_audio() is None
        assert buffer.get_preview_audio() is None

    def test_production_duration(self, buffer, audio_block):
        """Test production duration calculation."""
        buffer.add_voice_audio(audio_block)
        buffer.add_voice_audio(audio_block)

        assert buffer.production_duration == 1.0  # 2 blocks * 0.5s


class TestPreviewManager:
    """Tests for PreviewManager class."""

    @pytest.fixture
    def manager(self):
        """Create preview manager."""
        return PreviewManager(update_interval=0.1, timeout=1.0)

    def test_initialization(self, manager):
        """Test manager initializes correctly."""
        assert manager.update_interval == 0.1
        assert manager.timeout == 1.0

    def test_should_update_timing(self, manager):
        """Test update timing logic."""
        # Just created, should not update yet (internal timing)
        # After waiting, should allow update
        manager._last_update_time = time.time() - 0.2  # Simulate 200ms ago

        assert manager.should_update()

    def test_mark_updated_resets_timer(self, manager):
        """Test marking update resets timer."""
        manager._last_update_time = time.time() - 1.0  # 1 second ago
        assert manager.should_update()

        manager.mark_updated()
        # After marking, should not immediately allow another update
        assert not manager.should_update()


class TestProductionManager:
    """Tests for ProductionManager class."""

    @pytest.fixture
    def manager(self):
        """Create production manager."""
        return ProductionManager()

    @pytest.fixture
    def buffer(self):
        """Create buffer for testing."""
        return AudioBuffer(
            max_production_seconds=5.0,
            preview_window_seconds=2.0,
            block_seconds=0.5,
        )

    @pytest.fixture
    def mock_phrase_detector(self):
        """Create mock phrase detector."""
        class MockPhraseDetector:
            def __init__(self):
                self._phrase_end = False

            def is_phrase_end(self, is_silent):
                return self._phrase_end

            def set_phrase_end(self, value):
                self._phrase_end = value

        return MockPhraseDetector()

    def test_empty_buffer_no_flush(self, manager, buffer, mock_phrase_detector):
        """Test empty buffer never triggers flush."""
        assert not manager.should_flush(buffer, mock_phrase_detector, is_silent=True)

    def test_overflow_triggers_flush(self, manager, buffer, mock_phrase_detector):
        """Test buffer overflow triggers flush."""
        audio = np.random.randn(8000).astype(np.float32)

        # Fill to overflow
        for _ in range(buffer.max_production_blocks):
            buffer.add_voice_audio(audio)

        assert manager.should_flush(buffer, mock_phrase_detector, is_silent=True)

    def test_phrase_end_triggers_flush(self, manager, buffer, mock_phrase_detector):
        """Test phrase end detection triggers flush."""
        audio = np.random.randn(8000).astype(np.float32)
        buffer.add_voice_audio(audio)

        mock_phrase_detector.set_phrase_end(True)

        assert manager.should_flush(buffer, mock_phrase_detector, is_silent=True)

    def test_no_phrase_end_no_flush(self, manager, buffer, mock_phrase_detector):
        """Test no phrase end means no flush."""
        audio = np.random.randn(8000).astype(np.float32)
        buffer.add_voice_audio(audio)

        mock_phrase_detector.set_phrase_end(False)

        assert not manager.should_flush(buffer, mock_phrase_detector, is_silent=True)
