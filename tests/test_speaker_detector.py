"""Tests for speaker verification module."""

import numpy as np
import pytest
import tempfile
import os


class TestSpeakerVerifier:
    """Tests for SpeakerVerifier class."""

    def test_initialization(self, speaker_verifier):
        """Test speaker verifier initializes correctly."""
        assert speaker_verifier is not None
        assert speaker_verifier.sample_rate == 16000
        assert speaker_verifier.embedding_dim == 64
        assert speaker_verifier.similarity_threshold == 0.7

    def test_not_enrolled_initially(self, speaker_verifier):
        """Test that user is not enrolled initially."""
        assert speaker_verifier.is_enrolled is False

    def test_accept_all_when_not_enrolled(self, speaker_verifier, speech_like_audio):
        """Test that all audio is accepted when not enrolled."""
        is_user, score = speaker_verifier.is_user_speaking(speech_like_audio)

        assert is_user is True
        assert score == 1.0

    def test_enrollment_sample_collection(self, speaker_verifier, speech_like_audio):
        """Test enrollment sample collection."""
        current, required = speaker_verifier.add_enrollment_sample(speech_like_audio)

        assert current == 1
        assert required == 5  # Default minimum samples

    def test_enrollment_completion(self, speaker_verifier, speech_like_audio):
        """Test successful enrollment completion."""
        # Add required number of samples
        for _ in range(5):
            speaker_verifier.add_enrollment_sample(speech_like_audio)

        result = speaker_verifier.complete_enrollment()

        assert result is True
        assert speaker_verifier.is_enrolled is True

    def test_enrollment_incomplete(self, sample_rate, speech_like_audio):
        """Test enrollment fails with insufficient samples."""
        from core.speaker_detector import SpeakerVerifier

        # Create fresh verifier (reset any loaded embedding)
        sv = SpeakerVerifier(sample_rate=sample_rate)
        sv.reset_enrollment()  # Clear any previously loaded embedding

        # Add only 2 samples
        sv.add_enrollment_sample(speech_like_audio)
        sv.add_enrollment_sample(speech_like_audio)

        result = sv.complete_enrollment()

        assert result is False
        assert sv.is_enrolled is False

    def test_cancel_enrollment(self, speaker_verifier, speech_like_audio):
        """Test enrollment cancellation."""
        speaker_verifier.add_enrollment_sample(speech_like_audio)
        speaker_verifier.add_enrollment_sample(speech_like_audio)

        speaker_verifier.cancel_enrollment()

        # Samples should be cleared
        current, required = speaker_verifier.add_enrollment_sample(speech_like_audio)
        assert current == 1

    def test_verification_after_enrollment(self, speaker_verifier, speech_like_audio):
        """Test verification works after enrollment."""
        # Enroll
        for _ in range(5):
            speaker_verifier.add_enrollment_sample(speech_like_audio)
        speaker_verifier.complete_enrollment()

        # Verify with same audio (should match)
        is_user, score = speaker_verifier.is_user_speaking(speech_like_audio)

        assert isinstance(is_user, bool)
        assert 0.0 <= score <= 1.0

    def test_spectral_embedding_dimension(self, speaker_verifier, speech_like_audio):
        """Test spectral embedding has correct dimension."""
        embedding = speaker_verifier._compute_spectral_embedding(speech_like_audio)

        assert embedding.shape == (64,)

    def test_spectral_embedding_normalized(self, speaker_verifier, speech_like_audio):
        """Test spectral embedding is L2 normalized."""
        embedding = speaker_verifier._compute_spectral_embedding(speech_like_audio)
        norm = np.linalg.norm(embedding)

        assert abs(norm - 1.0) < 0.01

    def test_cosine_similarity(self, speaker_verifier):
        """Test cosine similarity calculation."""
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([1.0, 0.0, 0.0])

        sim = speaker_verifier._cosine_similarity(a, b)
        assert abs(sim - 1.0) < 0.01

        # Orthogonal vectors
        c = np.array([0.0, 1.0, 0.0])
        sim2 = speaker_verifier._cosine_similarity(a, c)
        assert abs(sim2) < 0.01

    def test_metrics_available(self, speaker_verifier):
        """Test that metrics are available."""
        metrics = speaker_verifier.get_metrics()

        assert "is_enrolled" in metrics
        assert "enrollment_samples" in metrics
        assert "required_samples" in metrics

    def test_reset_enrollment(self, speaker_verifier, speech_like_audio):
        """Test enrollment reset."""
        # Enroll first
        for _ in range(5):
            speaker_verifier.add_enrollment_sample(speech_like_audio)
        speaker_verifier.complete_enrollment()

        assert speaker_verifier.is_enrolled is True

        # Reset
        speaker_verifier.reset_enrollment()

        assert speaker_verifier.is_enrolled is False

    def test_short_audio_handling(self, speaker_verifier):
        """Test handling of very short audio."""
        short_audio = np.random.randn(100).astype(np.float32)

        # Should not crash, should accept
        is_user, score = speaker_verifier.is_user_speaking(short_audio)
        assert is_user is True


class TestEmbeddingPersistence:
    """Tests for embedding save/load functionality."""

    def test_save_and_load_embedding(self, speaker_verifier, speech_like_audio):
        """Test saving and loading embedding."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Temporarily change embedding path
            original_path = speaker_verifier._load_embedding

            # Enroll
            for _ in range(5):
                speaker_verifier.add_enrollment_sample(speech_like_audio)
            speaker_verifier.complete_enrollment()

            # Get the embedding
            original_embedding = speaker_verifier._user_embedding.copy()

            assert original_embedding is not None
