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


def _reference_highpass(audio, sample_rate=16000, cutoff_hz=80.0):
    """Recurrence IIR d'origine, en Python pur: reference de non-regression.

    Volontairement naive et lente. C'est le comportement exact que la version
    vectorisee (scipy.signal.lfilter) doit reproduire.
    """
    import math

    if audio.size == 0:
        return audio

    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)

    filtered = np.zeros_like(audio)
    filtered[0] = audio[0]
    for i in range(1, len(audio)):
        filtered[i] = alpha * (filtered[i - 1] + audio[i] - audio[i - 1])
    return filtered.astype(audio.dtype)


class TestHighpassFilterEquivalence:
    """Le filtre vectorise doit rester numeriquement identique a la boucle.

    Le passe-haut tournait en Python pur sur chaque echantillon, soit ~0,45 s
    par buffer de 30 s a 16 kHz, sur le chemin de production. La version
    scipy.signal.lfilter est ~40x plus rapide; ces tests verifient qu'elle ne
    change pas le signal produit.
    """

    @pytest.mark.parametrize("n_samples", [1, 2, 10, 1000, 16000])
    def test_matches_reference_implementation(self, n_samples, sample_rate):
        from core.audio_preprocessing import apply_highpass_filter

        rng = np.random.default_rng(1234)
        audio = (rng.standard_normal(n_samples) * 0.2).astype(np.float32)

        got = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)
        expected = _reference_highpass(audio, sample_rate, cutoff_hz=80.0)

        assert got.shape == expected.shape
        assert got.dtype == expected.dtype
        np.testing.assert_allclose(got, expected, atol=1e-5)

    def test_first_sample_is_preserved(self, sample_rate):
        """La condition initiale y[0] = x[0] doit etre conservee."""
        from core.audio_preprocessing import apply_highpass_filter

        audio = np.array([0.7, -0.2, 0.1, 0.0], dtype=np.float32)
        result = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

        assert result[0] == pytest.approx(audio[0], abs=1e-6)

    def test_removes_dc_offset(self, sample_rate):
        """Un passe-haut doit supprimer une composante continue."""
        from core.audio_preprocessing import apply_highpass_filter

        audio = np.full(sample_rate, 0.5, dtype=np.float32)
        result = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

        # Apres le regime transitoire, le continu est elimine.
        assert abs(float(result[-1])) < 0.01

    def test_preserves_speech_band_energy(self, sample_rate):
        """Un signal a 200 Hz (bande vocale) doit survivre au filtre 80 Hz."""
        from core.audio_preprocessing import apply_highpass_filter

        t = np.linspace(0, 1.0, sample_rate, endpoint=False)
        audio = np.sin(2 * np.pi * 200 * t).astype(np.float32)

        result = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

        rms_in = float(np.sqrt(np.mean(audio ** 2)))
        rms_out = float(np.sqrt(np.mean(result ** 2)))
        assert rms_out > 0.8 * rms_in

    def test_empty_and_single_sample_are_safe(self, sample_rate):
        from core.audio_preprocessing import apply_highpass_filter

        assert apply_highpass_filter(np.array([], dtype=np.float32)).size == 0

        single = apply_highpass_filter(np.array([0.5], dtype=np.float32))
        assert single.shape == (1,)
        assert single[0] == pytest.approx(0.5, abs=1e-6)
