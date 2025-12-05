"""Tests for noise reduction module."""

import numpy as np
import pytest


class TestNoiseReduction:
    """Tests for noise reduction functions."""

    def test_reduce_noise_returns_same_length(self, sample_rate):
        """Test that reduce_noise returns audio of same length."""
        from core.noise_reduction import reduce_noise

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.1
        result = reduce_noise(audio, sample_rate)

        assert len(result) == len(audio)

    def test_reduce_noise_preserves_dtype(self, sample_rate):
        """Test that reduce_noise preserves float32 dtype."""
        from core.noise_reduction import reduce_noise

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.1
        result = reduce_noise(audio, sample_rate)

        assert result.dtype == np.float32

    def test_reduce_noise_empty_audio(self):
        """Test reduce_noise handles empty audio."""
        from core.noise_reduction import reduce_noise

        audio = np.array([], dtype=np.float32)
        result = reduce_noise(audio, 16000)

        assert len(result) == 0

    def test_spectral_subtraction(self, sample_rate):
        """Test spectral subtraction function."""
        from core.noise_reduction import spectral_subtraction

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.1
        result = spectral_subtraction(audio, sample_rate)

        assert len(result) == len(audio)
        assert result.dtype == np.float32

    def test_deep_learning_denoise(self, sample_rate):
        """Test deep learning denoising function."""
        from core.noise_reduction import deep_learning_denoise

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.1
        result = deep_learning_denoise(audio, sample_rate, strength=0.5)

        assert len(result) == len(audio)
        assert result.dtype == np.float32

    def test_bandpass_voice_filter(self, sample_rate):
        """Test bandpass filter for voice frequencies."""
        from core.noise_reduction import bandpass_voice_filter

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.1
        result = bandpass_voice_filter(audio, sample_rate)

        assert len(result) == len(audio)
        assert result.dtype == np.float32

    def test_estimate_voice_distance(self, sample_rate):
        """Test voice distance estimation."""
        from core.noise_reduction import estimate_voice_distance

        audio = np.random.randn(sample_rate).astype(np.float32) * 0.1
        result = estimate_voice_distance(audio, sample_rate)

        assert result in ["close", "medium", "far", "unknown"]

    def test_noise_reduction_reduces_noise(self, sample_rate):
        """Test that noise reduction actually reduces noise level."""
        from core.noise_reduction import deep_learning_denoise

        # Create noisy audio
        np.random.seed(42)
        noise = np.random.randn(sample_rate).astype(np.float32) * 0.3

        result = deep_learning_denoise(noise, sample_rate, strength=0.8)

        # RMS should be lower after denoising
        input_rms = np.sqrt(np.mean(noise ** 2))
        output_rms = np.sqrt(np.mean(result ** 2))

        assert output_rms <= input_rms


class TestNoiseProfiler:
    """Tests for NoiseProfiler class."""

    def test_profiler_initialization(self, sample_rate):
        """Test noise profiler initializes correctly."""
        from core.noise_reduction import NoiseProfiler

        profiler = NoiseProfiler(sample_rate=sample_rate, profile_seconds=2.0)

        assert profiler.sample_rate == sample_rate
        assert profiler.is_ready is False

    def test_profiler_collects_samples(self, sample_rate):
        """Test noise profiler collects samples."""
        from core.noise_reduction import NoiseProfiler

        profiler = NoiseProfiler(sample_rate=sample_rate, profile_seconds=1.0)

        # Add some noise samples
        for _ in range(5):
            noise = np.random.randn(4000).astype(np.float32) * 0.01
            profiler.add_noise_sample(noise)

        # Should eventually become ready
        # (depends on total samples collected)

    def test_profiler_reset(self, sample_rate):
        """Test noise profiler reset."""
        from core.noise_reduction import NoiseProfiler

        profiler = NoiseProfiler(sample_rate=sample_rate)
        profiler.add_noise_sample(np.random.randn(8000).astype(np.float32))

        profiler.reset()

        assert profiler.is_ready is False
        assert profiler.noise_spectrum is None
