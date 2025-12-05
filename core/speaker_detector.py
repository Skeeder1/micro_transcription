"""Speaker verification for distinguishing user voice from others.

This module provides speaker embedding and verification to differentiate
the user's voice from other speakers (TV, radio, other people).

Uses simple spectral features when pyannote is not available,
or full speaker embeddings when it is.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import numpy as np

from shared import config


class SpeakerVerifier:
    """
    Verifies if audio comes from the registered user.

    Uses spectral embeddings to create a voice fingerprint
    and compare new audio against it.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        embedding_dim: int = 64,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize speaker verifier.

        Args:
            sample_rate: Audio sample rate in Hz
            embedding_dim: Dimension of spectral embedding
            similarity_threshold: Minimum similarity to accept as user (0.0-1.0)
        """
        self.sample_rate = sample_rate
        self.embedding_dim = embedding_dim
        self.similarity_threshold = similarity_threshold

        # User embedding (loaded or computed)
        self._user_embedding: Optional[np.ndarray] = None
        self._is_enrolled: bool = False

        # Enrollment state
        self._enrollment_samples: list[np.ndarray] = []
        self._min_enrollment_samples: int = 5  # Need at least 5 samples

        # Try to load existing embedding
        self._load_embedding()

    def _load_embedding(self) -> None:
        """Load user embedding from file if exists."""
        embedding_path = getattr(config, 'SPEAKER_EMBEDDING_PATH', 'data/user_embedding.npy')

        try:
            path = Path(embedding_path)
            if path.exists():
                self._user_embedding = np.load(path)
                self._is_enrolled = True
                print(f"Empreinte vocale chargée depuis {embedding_path}")
        except Exception as e:
            print(f"Impossible de charger l'empreinte vocale: {e}")

    def _save_embedding(self) -> None:
        """Save user embedding to file."""
        if self._user_embedding is None:
            return

        embedding_path = getattr(config, 'SPEAKER_EMBEDDING_PATH', 'data/user_embedding.npy')

        try:
            path = Path(embedding_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.save(path, self._user_embedding)
            print(f"Empreinte vocale sauvegardée dans {embedding_path}")
        except Exception as e:
            print(f"Impossible de sauvegarder l'empreinte vocale: {e}")

    def _compute_spectral_embedding(self, audio: np.ndarray) -> np.ndarray:
        """
        Compute spectral embedding from audio.

        Uses MFCC-like features as a simple but effective speaker embedding.

        Args:
            audio: Audio signal (numpy array)

        Returns:
            Embedding vector of shape (embedding_dim,)
        """
        try:
            from scipy.fft import rfft
            from scipy.signal import get_window
        except ImportError:
            # Fallback: use numpy for basic spectral analysis
            return self._compute_basic_embedding(audio)

        # Parameters
        frame_size = 512  # ~32ms at 16kHz
        hop_size = 256
        n_mels = self.embedding_dim

        if len(audio) < frame_size:
            audio = np.pad(audio, (0, frame_size - len(audio)))

        # Apply windowing and compute FFT for each frame
        window = get_window('hann', frame_size)
        n_frames = (len(audio) - frame_size) // hop_size + 1

        if n_frames < 1:
            n_frames = 1

        # Compute magnitude spectrum for each frame
        spectra = []
        for i in range(n_frames):
            start = i * hop_size
            frame = audio[start:start + frame_size] * window
            spectrum = np.abs(rfft(frame))
            spectra.append(spectrum)

        # Average spectrum
        avg_spectrum = np.mean(spectra, axis=0)

        # Simple mel-like binning
        n_fft_bins = len(avg_spectrum)
        mel_bins = np.linspace(0, n_fft_bins, n_mels + 1).astype(int)

        embedding = np.zeros(n_mels)
        for i in range(n_mels):
            start_bin = mel_bins[i]
            end_bin = mel_bins[i + 1]
            if end_bin > start_bin:
                embedding[i] = np.mean(avg_spectrum[start_bin:end_bin])

        # Log compression
        embedding = np.log1p(embedding)

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 1e-10:
            embedding = embedding / norm

        return embedding

    def _compute_basic_embedding(self, audio: np.ndarray) -> np.ndarray:
        """Fallback embedding using basic numpy operations."""
        # Simple FFT-based embedding
        n = min(len(audio), 8192)
        audio_chunk = audio[:n]

        # Compute magnitude spectrum
        spectrum = np.abs(np.fft.rfft(audio_chunk))

        # Downsample to embedding_dim
        indices = np.linspace(0, len(spectrum) - 1, self.embedding_dim).astype(int)
        embedding = spectrum[indices]

        # Log compression
        embedding = np.log1p(embedding)

        # L2 normalize
        norm = np.linalg.norm(embedding)
        if norm > 1e-10:
            embedding = embedding / norm

        return embedding

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two vectors."""
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a < 1e-10 or norm_b < 1e-10:
            return 0.0

        return float(dot / (norm_a * norm_b))

    @property
    def is_enrolled(self) -> bool:
        """Check if user is enrolled."""
        return self._is_enrolled

    def add_enrollment_sample(self, audio: np.ndarray) -> tuple[int, int]:
        """
        Add an audio sample for user enrollment.

        Args:
            audio: Audio sample from user

        Returns:
            Tuple of (current_samples, required_samples)
        """
        if len(audio) < 4000:  # Need at least 0.25s of audio
            return len(self._enrollment_samples), self._min_enrollment_samples

        self._enrollment_samples.append(audio.copy())
        return len(self._enrollment_samples), self._min_enrollment_samples

    def complete_enrollment(self) -> bool:
        """
        Complete enrollment by computing user embedding from collected samples.

        Returns:
            True if enrollment successful, False otherwise
        """
        if len(self._enrollment_samples) < self._min_enrollment_samples:
            print(f"Pas assez d'échantillons ({len(self._enrollment_samples)}/{self._min_enrollment_samples})")
            return False

        # Compute embedding for each sample
        embeddings = []
        for sample in self._enrollment_samples:
            emb = self._compute_spectral_embedding(sample)
            embeddings.append(emb)

        # Average all embeddings
        self._user_embedding = np.mean(embeddings, axis=0)

        # L2 normalize final embedding
        norm = np.linalg.norm(self._user_embedding)
        if norm > 1e-10:
            self._user_embedding = self._user_embedding / norm

        self._is_enrolled = True
        self._enrollment_samples.clear()

        # Save to file
        self._save_embedding()

        print("Enregistrement de l'empreinte vocale terminé!")
        return True

    def cancel_enrollment(self) -> None:
        """Cancel ongoing enrollment and clear samples."""
        self._enrollment_samples.clear()

    def is_user_speaking(self, audio: np.ndarray, debug: bool = False) -> tuple[bool, float]:
        """
        Check if the audio matches the enrolled user's voice.

        Args:
            audio: Audio to verify
            debug: Print debug information

        Returns:
            Tuple of (is_user, similarity_score)
        """
        if not self._is_enrolled or self._user_embedding is None:
            # Not enrolled = accept all voices
            return True, 1.0

        if len(audio) < 2000:  # Need at least 0.125s
            return True, 1.0  # Too short to judge

        # Compute embedding for current audio
        current_embedding = self._compute_spectral_embedding(audio)

        # Compute similarity
        similarity = self._cosine_similarity(current_embedding, self._user_embedding)

        threshold = getattr(config, 'SPEAKER_SIMILARITY_THRESHOLD', self.similarity_threshold)
        is_user = similarity >= threshold

        if debug:
            status = "UTILISATEUR" if is_user else "AUTRE"
            print(f"[SPEAKER] Similarité={similarity:.3f} seuil={threshold} → {status}")

        return is_user, similarity

    def reset_enrollment(self) -> None:
        """Reset enrollment and delete saved embedding."""
        self._user_embedding = None
        self._is_enrolled = False
        self._enrollment_samples.clear()

        embedding_path = getattr(config, 'SPEAKER_EMBEDDING_PATH', 'data/user_embedding.npy')
        try:
            path = Path(embedding_path)
            if path.exists():
                path.unlink()
                print(f"Empreinte vocale supprimée: {embedding_path}")
        except Exception as e:
            print(f"Erreur suppression empreinte: {e}")

    def get_metrics(self) -> dict[str, float]:
        """Get current speaker verification metrics."""
        return {
            "is_enrolled": 1.0 if self._is_enrolled else 0.0,
            "enrollment_samples": float(len(self._enrollment_samples)),
            "required_samples": float(self._min_enrollment_samples),
        }
