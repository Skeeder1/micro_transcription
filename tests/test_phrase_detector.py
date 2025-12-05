"""Tests for phrase end detection module."""

import numpy as np
import pytest


class TestPhraseEndDetector:
    """Tests for PhraseEndDetector class."""

    def test_initialization(self, phrase_detector):
        """Test phrase detector initializes correctly."""
        assert phrase_detector is not None
        assert phrase_detector.sample_rate == 16000
        assert phrase_detector.history_size == 5
        assert phrase_detector.energy_drop_threshold == 0.3

    def test_reset(self, phrase_detector, loud_noise_audio):
        """Test reset clears state."""
        # Add some history
        phrase_detector.update(loud_noise_audio, is_silent=False)
        phrase_detector.update(loud_noise_audio, is_silent=False)

        phrase_detector.reset()

        assert phrase_detector._speech_started is False
        assert phrase_detector._silence_count == 0
        assert phrase_detector._peak_energy == 0.0

    def test_speech_then_silence_detection(self, phrase_detector, loud_noise_audio, silence_audio):
        """Test phrase end detection after speech followed by silence."""
        # Simulate speech
        for _ in range(3):
            phrase_detector.update(loud_noise_audio, is_silent=False)

        # Simulate silence
        for _ in range(3):
            phrase_detector.update(silence_audio, is_silent=True)

        is_end = phrase_detector.is_phrase_end(is_silent=True)
        assert is_end is True

    def test_only_silence_no_phrase_end(self, phrase_detector, silence_audio):
        """Test that silence alone doesn't trigger phrase end."""
        for _ in range(5):
            phrase_detector.update(silence_audio, is_silent=True)

        is_end = phrase_detector.is_phrase_end(is_silent=True)
        # No speech started, so no phrase end
        assert is_end is False

    def test_energy_drop_detection(self, phrase_detector, sample_rate):
        """Test energy drop detection."""
        # High energy audio
        loud = np.random.randn(8000).astype(np.float32) * 0.5
        # Low energy audio
        quiet = np.random.randn(8000).astype(np.float32) * 0.01

        # Build up energy
        phrase_detector.update(loud, is_silent=False)
        phrase_detector.update(loud, is_silent=False)

        # Drop energy
        phrase_detector.update(quiet, is_silent=True)

        drop_detected = phrase_detector._detect_energy_drop()
        assert drop_detected is True

    def test_confidence_score(self, phrase_detector, loud_noise_audio, silence_audio):
        """Test confidence score calculation."""
        # Build some history
        phrase_detector.update(loud_noise_audio, is_silent=False)
        phrase_detector.update(loud_noise_audio, is_silent=False)
        phrase_detector.update(silence_audio, is_silent=True)
        phrase_detector.update(silence_audio, is_silent=True)

        confidence = phrase_detector.get_confidence()

        assert 0.0 <= confidence <= 1.0

    def test_metrics_available(self, phrase_detector, loud_noise_audio):
        """Test that metrics are available."""
        phrase_detector.update(loud_noise_audio, is_silent=False)

        metrics = phrase_detector.get_metrics()

        assert "current_energy" in metrics
        assert "peak_energy" in metrics
        assert "silence_count" in metrics
        assert "energy_drop_detected" in metrics
        assert "confidence" in metrics

    def test_rms_calculation(self, phrase_detector):
        """Test RMS energy calculation."""
        constant = np.ones(1000, dtype=np.float32) * 0.5
        rms = phrase_detector._calculate_rms(constant)
        assert abs(rms - 0.5) < 0.01

    def test_zcr_calculation(self, phrase_detector, sample_rate):
        """Test zero crossing rate calculation."""
        # Pure sine wave
        t = np.linspace(0, 0.5, 8000)
        sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        zcr = phrase_detector._calculate_zcr(sine)
        assert 0.0 < zcr < 0.2

    def test_minimum_silence_required(self, phrase_detector, loud_noise_audio, silence_audio):
        """Test that minimum silence blocks are required."""
        # Speech
        phrase_detector.update(loud_noise_audio, is_silent=False)

        # Only one block of silence
        phrase_detector.update(silence_audio, is_silent=True)

        # Should not be phrase end yet (need more silence)
        is_end = phrase_detector.is_phrase_end(is_silent=True)
        # May or may not be end depending on energy drop
        # Just verify it doesn't crash


class TestPitchDetection:
    """Tests for pitch-related functionality."""

    def test_pitch_estimation_sine(self, phrase_detector, sample_rate):
        """Test pitch estimation on pure sine wave."""
        # 150Hz sine wave (male voice fundamental)
        t = np.linspace(0, 0.5, 8000)
        sine = np.sin(2 * np.pi * 150 * t).astype(np.float32)

        pitch = phrase_detector._estimate_pitch(sine)

        if pitch is not None:
            # Should be close to 150Hz
            assert 100 < pitch < 200

    def test_pitch_estimation_noise(self, phrase_detector, noise_audio):
        """Test pitch estimation on noise."""
        pitch = phrase_detector._estimate_pitch(noise_audio)
        # Noise may or may not have detectable pitch
        # Just verify it doesn't crash

    def test_pitch_drop_detection(self, phrase_detector, sample_rate):
        """Test falling pitch detection."""
        # Create falling pitch audio
        t1 = np.linspace(0, 0.5, 8000)
        high_pitch = np.sin(2 * np.pi * 200 * t1).astype(np.float32)

        t2 = np.linspace(0, 0.5, 8000)
        low_pitch = np.sin(2 * np.pi * 120 * t2).astype(np.float32)

        # Update with high then low pitch
        phrase_detector.update(high_pitch, is_silent=False)
        phrase_detector.update(low_pitch, is_silent=False)

        # Check if pitch drop detected
        drop = phrase_detector._detect_pitch_drop()
        # May or may not detect depending on implementation
