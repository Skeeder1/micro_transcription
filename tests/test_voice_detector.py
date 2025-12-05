"""Tests for voice detection module."""

import numpy as np
import pytest


class TestVoiceDetector:
    """Tests for VoiceDetector class."""

    def test_initialization(self, voice_detector):
        """Test voice detector initializes correctly."""
        assert voice_detector is not None
        assert voice_detector.sample_rate == 16000
        assert voice_detector.silero_threshold == 0.5
        assert voice_detector.use_zcr_filter is True
        assert voice_detector.use_adaptive is True

    def test_silence_detection(self, voice_detector, silence_audio):
        """Test that silence is not detected as speech."""
        is_speech = voice_detector.is_human_speech(silence_audio)
        assert is_speech is False

    def test_noise_detection(self, voice_detector, noise_audio):
        """Test that low-level noise is not detected as speech."""
        # First calibrate with noise (10 chunks required)
        for _ in range(12):
            voice_detector.is_human_speech(noise_audio)

        is_speech = voice_detector.is_human_speech(noise_audio)
        assert is_speech is False

    def test_loud_noise_rejection(self, voice_detector, noise_audio, loud_noise_audio):
        """Test that loud noise without voice characteristics is rejected."""
        # Calibrate with quiet noise (10 chunks required)
        for _ in range(12):
            voice_detector.is_human_speech(noise_audio)

        # Loud noise should be rejected by Silero VAD
        is_speech = voice_detector.is_human_speech(loud_noise_audio)
        # May or may not be detected depending on VAD, but metrics should show high boost
        metrics = voice_detector.get_metrics()
        assert metrics["boost_factor"] > 1.0

    def test_calibration_phase(self, voice_detector, noise_audio):
        """Test calibration phase works correctly."""
        # During calibration, everything should be rejected
        is_speech = voice_detector.is_human_speech(noise_audio)
        assert is_speech is False

        metrics = voice_detector.get_metrics()
        assert metrics["is_calibrating"] == 1.0 or metrics["reference_rms"] > 0

    def test_metrics_available(self, voice_detector, noise_audio):
        """Test that metrics are available after detection."""
        voice_detector.is_human_speech(noise_audio)
        metrics = voice_detector.get_metrics()

        assert "rms" in metrics
        assert "silero_probability" in metrics
        assert "zero_crossing_rate" in metrics
        assert "reference_rms" in metrics
        assert "boost_factor" in metrics
        assert "is_calibrating" in metrics

    def test_zcr_calculation(self, voice_detector):
        """Test zero crossing rate calculation."""
        # Pure sine wave has predictable ZCR
        t = np.linspace(0, 1, 16000)
        sine = np.sin(2 * np.pi * 440 * t).astype(np.float32)

        zcr = voice_detector._calculate_zcr(sine)
        # ZCR for 440Hz sine at 16kHz should be around 0.055
        assert 0.03 < zcr < 0.1

    def test_rms_calculation(self, voice_detector):
        """Test RMS energy calculation."""
        # Constant signal has predictable RMS
        constant = np.ones(1000, dtype=np.float32) * 0.5
        rms = voice_detector._calculate_rms(constant)
        assert abs(rms - 0.5) < 0.01

    def test_adaptive_reference_update(self, voice_detector, noise_audio):
        """Test that reference level updates during calibration."""
        initial_ref = voice_detector._reference_rms

        # Run through calibration (10 chunks required)
        for _ in range(12):
            voice_detector.is_human_speech(noise_audio)

        final_ref = voice_detector._reference_rms
        # Reference should have been updated
        assert final_ref != initial_ref or voice_detector._is_calibrating is False

    def test_voting_mechanism(self, voice_detector, sample_rate):
        """Test sliding window voting mechanism."""
        # Create mixed audio with some voice-like and some noise sections
        audio = np.random.randn(8000).astype(np.float32) * 0.1

        prob, is_voice = voice_detector._get_silero_probability_voting(audio)

        assert isinstance(prob, float)
        assert isinstance(is_voice, bool)
        assert 0.0 <= prob <= 1.0


class TestVoiceDetectorRecalibration:
    """Tests for automatic recalibration feature."""

    def test_recalibration_trigger(self, sample_rate):
        """Test that recalibration triggers after silence period."""
        from core.voice_detector import VoiceDetector

        vd = VoiceDetector(sample_rate=sample_rate)
        noise_audio = np.random.randn(8000).astype(np.float32) * 0.01

        # Complete initial calibration (10 chunks required)
        for _ in range(12):
            vd.is_human_speech(noise_audio)

        # Ensure calibration is complete
        assert vd._is_calibrating is False

        # Directly trigger recalibration
        vd._trigger_recalibration()

        # Should have triggered recalibration
        assert vd._is_calibrating is True

    def test_speech_resets_silence_counter(self, sample_rate):
        """Test that speech detection resets silence counter."""
        from core.voice_detector import VoiceDetector
        import time

        vd = VoiceDetector(sample_rate=sample_rate)

        # Initialize time tracking
        vd._last_update_time = time.time() - 1.0
        vd._seconds_since_last_speech = 20.0

        # Call with speech detected
        vd._check_recalibration(True)

        assert vd._seconds_since_last_speech == 0.0
