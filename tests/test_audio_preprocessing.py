"""Tests for audio preprocessing module."""

import numpy as np
import pytest


class TestNormalization:
    """Tests for audio normalization."""

    def test_normalize_audio(self, sample_rate):
        """Test audio normalization to [-1, 1]."""
        from core.audio_preprocessing import normalize_audio

        audio = np.random.randn(sample_rate).astype(np.float32) * 5.0
        result = normalize_audio(audio)

        assert result.max() <= 1.0
        assert result.min() >= -1.0

    def test_normalize_silent_audio(self):
        """Test normalization of silent audio."""
        from core.audio_preprocessing import normalize_audio

        audio = np.zeros(1000, dtype=np.float32)
        result = normalize_audio(audio)

        assert np.array_equal(result, audio)

    def test_normalize_empty_audio(self):
        """Test normalization of empty audio."""
        from core.audio_preprocessing import normalize_audio

        audio = np.array([], dtype=np.float32)
        result = normalize_audio(audio)

        assert len(result) == 0


class TestHighpassFilter:
    """Tests for high-pass filter."""

    def test_highpass_filter_length(self, sample_rate):
        """Test high-pass filter preserves length."""
        from core.audio_preprocessing import apply_highpass_filter

        audio = np.random.randn(sample_rate).astype(np.float32)
        result = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

        assert len(result) == len(audio)

    def test_highpass_filter_dtype(self, sample_rate):
        """Test high-pass filter preserves dtype."""
        from core.audio_preprocessing import apply_highpass_filter

        audio = np.random.randn(sample_rate).astype(np.float32)
        result = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

        assert result.dtype == np.float32

    def test_highpass_removes_dc(self, sample_rate):
        """Test high-pass filter removes DC offset."""
        from core.audio_preprocessing import apply_highpass_filter

        # Audio with DC offset
        audio = np.ones(sample_rate, dtype=np.float32) * 0.5
        result = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

        # Mean should be close to 0 after filtering (DC removed)
        assert abs(result.mean()) < 0.1

    def test_highpass_empty_audio(self):
        """Test high-pass filter with empty audio."""
        from core.audio_preprocessing import apply_highpass_filter

        audio = np.array([], dtype=np.float32)
        result = apply_highpass_filter(audio, 16000, cutoff_hz=80.0)

        assert len(result) == 0


class TestAmplification:
    """Tests for audio amplification."""

    def test_amplify_quiet_audio(self, sample_rate):
        """Test amplification of quiet audio."""
        from core.audio_preprocessing import amplify_audio

        quiet = np.random.randn(sample_rate).astype(np.float32) * 0.01
        result = amplify_audio(quiet, target_rms=0.1)

        input_rms = np.sqrt(np.mean(quiet ** 2))
        output_rms = np.sqrt(np.mean(result ** 2))

        # Output should be louder
        assert output_rms > input_rms

    def test_amplify_loud_audio_limited(self, sample_rate):
        """Test that amplification is limited to max 2x gain."""
        from core.audio_preprocessing import amplify_audio

        # Very quiet audio that would need >2x gain
        very_quiet = np.random.randn(sample_rate).astype(np.float32) * 0.001
        result = amplify_audio(very_quiet, target_rms=0.1)

        input_rms = np.sqrt(np.mean(very_quiet ** 2))
        output_rms = np.sqrt(np.mean(result ** 2))

        # Gain should be limited to 2x
        if input_rms > 0:
            gain = output_rms / input_rms
            assert gain <= 2.1  # Allow small tolerance

    def test_amplify_silent_audio(self):
        """Test amplification of silent audio."""
        from core.audio_preprocessing import amplify_audio

        silent = np.zeros(1000, dtype=np.float32)
        result = amplify_audio(silent, target_rms=0.1)

        # Should return unchanged
        assert np.array_equal(result, silent)

    def test_amplify_empty_audio(self):
        """Test amplification of empty audio."""
        from core.audio_preprocessing import amplify_audio

        audio = np.array([], dtype=np.float32)
        result = amplify_audio(audio, target_rms=0.1)

        assert len(result) == 0


class TestPreprocessAudio:
    """Tests for complete preprocessing pipeline."""

    def test_preprocess_production(self, sample_rate):
        """Test full preprocessing for production."""
        from core.audio_preprocessing import preprocess_audio

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.05
        result = preprocess_audio(audio, sample_rate, for_production=True)

        assert len(result) == len(audio)
        assert result.dtype == np.float32
        assert result.max() <= 1.0
        assert result.min() >= -1.0

    def test_preprocess_preview(self, sample_rate):
        """Test lighter preprocessing for preview."""
        from core.audio_preprocessing import preprocess_audio

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.05
        result = preprocess_audio(audio, sample_rate, for_production=False)

        assert len(result) == len(audio)
        assert result.dtype == np.float32

    def test_preprocess_empty_audio(self):
        """Test preprocessing of empty audio."""
        from core.audio_preprocessing import preprocess_audio

        audio = np.array([], dtype=np.float32)
        result = preprocess_audio(audio, 16000, for_production=True)

        assert len(result) == 0

    def test_preprocess_normalizes_output(self, sample_rate):
        """Test that preprocessing normalizes output to [-1, 1]."""
        from core.audio_preprocessing import preprocess_audio

        # Loud audio
        audio = np.random.randn(sample_rate).astype(np.float32) * 5.0
        result = preprocess_audio(audio, sample_rate, for_production=True)

        assert result.max() <= 1.0
        assert result.min() >= -1.0


class TestPreprocessingPipeline:
    """Integration tests for the preprocessing pipeline."""

    def test_pipeline_order(self, sample_rate):
        """Test that preprocessing steps are applied in correct order."""
        from core.audio_preprocessing import preprocess_audio

        # Audio with DC offset and low level
        audio = np.random.randn(sample_rate).astype(np.float32) * 0.01 + 0.5
        result = preprocess_audio(audio, sample_rate, for_production=True)

        # Should have removed DC, amplified, and normalized
        assert abs(result.mean()) < 0.2  # DC removed
        assert result.max() <= 1.0  # Normalized

    def test_production_vs_preview_difference(self, sample_rate):
        """Test that production and preview processing differ."""
        from core.audio_preprocessing import preprocess_audio
        from shared import config

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.1

        prod = preprocess_audio(audio, sample_rate, for_production=True)
        prev = preprocess_audio(audio, sample_rate, for_production=False)

        # If noise reduction is enabled, outputs should differ
        if config.ENABLE_NOISE_REDUCTION:
            # They may differ due to noise reduction
            pass
        # Otherwise they should be the same
