"""Advanced voice activity detection combining Silero VAD and Zero Crossing Rate.

This module provides human speech detection that distinguishes voice from ambient noise,
improving transcription accuracy and end-of-speech detection.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import torch


class VoiceDetector:
    """
    Detect human speech vs ambient noise using multiple criteria.

    Combines:
    - Silero VAD: ML-based voice probability (0.0-1.0)
    - Zero Crossing Rate: Distinguishes voice from white noise
    - RMS Energy: Fast pre-filter for silence

    Architecture:
    1. RMS check (fast rejection of pure silence)
    2. Silero VAD inference (main classifier)
    3. Optional ZCR validation (additional noise filter)
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silero_threshold: float = 0.5,
        rms_threshold: float = 0.003,
        use_zcr_filter: bool = True,
        zcr_min: float = 0.02,
        zcr_max: float = 0.30,
    ):
        """
        Initialize voice detector.

        Args:
            sample_rate: Audio sample rate (must match Silero: 8000 or 16000)
            silero_threshold: Probability threshold for voice (0.0-1.0, default 0.5)
            rms_threshold: Energy threshold for silence rejection
            use_zcr_filter: Enable Zero Crossing Rate filtering
            zcr_min: Minimum ZCR for voice (below = likely DC offset or hum)
            zcr_max: Maximum ZCR for voice (above = likely white noise)
        """
        self.sample_rate = sample_rate
        self.silero_threshold = silero_threshold
        self.rms_threshold = rms_threshold
        self.use_zcr_filter = use_zcr_filter
        self.zcr_min = zcr_min
        self.zcr_max = zcr_max

        # Lazy-load Silero VAD model
        self._model: Optional[torch.nn.Module] = None
        self._model_loaded = False

        # Cache for performance
        self._last_silero_prob: float = 0.0
        self._last_zcr: float = 0.0
        self._last_rms: float = 0.0

    def _load_model(self) -> None:
        """Load Silero VAD model (lazy initialization)."""
        if self._model_loaded:
            return

        try:
            # Load Silero VAD v4.0 from torch hub
            # Model is ~1MB, downloads automatically on first run
            torch.hub.set_dir(os.path.join(os.path.dirname(__file__), "..", ".cache", "torch"))

            model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,
            )

            self._model = model
            self._model_loaded = True

            # Set model to eval mode
            self._model.eval()

            print(f"✅ Silero VAD chargé (sample_rate={self.sample_rate}, threshold={self.silero_threshold})")

        except Exception as e:
            print(f"⚠️ Échec chargement Silero VAD: {e}")
            print("   → Mode dégradé: utilisation RMS uniquement")
            self._model_loaded = False

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS (Root Mean Square) energy."""
        return float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))

    def _calculate_zcr(self, audio: np.ndarray) -> float:
        """
        Calculate Zero Crossing Rate.

        ZCR is the rate at which the signal changes sign.
        - Low ZCR: monotonous sound (hum, DC offset)
        - Medium ZCR: voice (typical human speech)
        - High ZCR: white noise, hiss

        Returns:
            ZCR normalized by signal length (0.0-1.0)
        """
        if len(audio) < 2:
            return 0.0

        # Count sign changes
        signs = np.sign(audio)
        zero_crossings = np.sum(np.abs(np.diff(signs))) / 2.0

        # Normalize by length
        return float(zero_crossings / len(audio))

    def _get_silero_probability(self, audio: np.ndarray) -> float:
        """
        Get voice probability from Silero VAD.

        Silero VAD requires EXACTLY:
        - 512 samples for 16kHz sample rate
        - 256 samples for 8kHz sample rate

        Args:
            audio: Audio chunk (float32, 16kHz recommended)

        Returns:
            Probability of voice (0.0-1.0)
        """
        if self._model is None:
            return 0.0

        try:
            # Silero requires exact chunk sizes
            required_samples = 512 if self.sample_rate == 16000 else 256

            # Ensure audio is 1D
            if audio.ndim > 1:
                audio = audio.squeeze()

            # Resample/pad/trim to required size
            if len(audio) < required_samples:
                # Pad with zeros if too short
                audio = np.pad(audio, (0, required_samples - len(audio)), mode='constant')
            elif len(audio) > required_samples:
                # Use multiple windows and average probabilities
                num_windows = len(audio) // required_samples
                probabilities = []

                for i in range(num_windows):
                    start = i * required_samples
                    end = start + required_samples
                    chunk = audio[start:end]

                    audio_tensor = torch.from_numpy(chunk).float()

                    with torch.no_grad():
                        prob = self._model(audio_tensor, self.sample_rate).item()
                        probabilities.append(prob)

                # Return maximum probability (most likely voice segment)
                return float(max(probabilities)) if probabilities else 0.0
            else:
                # Exact size - perfect
                audio_tensor = torch.from_numpy(audio).float()

                with torch.no_grad():
                    probability = self._model(audio_tensor, self.sample_rate).item()

                return float(probability)

        except Exception as e:
            print(f"⚠️ Erreur Silero VAD: {e}")
            return 0.0

    def is_human_speech(
        self,
        audio: np.ndarray,
        debug: bool = False
    ) -> bool:
        """
        Detect if audio contains human speech vs ambient noise.

        Pipeline:
        1. RMS check → reject pure silence immediately
        2. Silero VAD → get ML probability of voice
        3. ZCR check → validate it's not white noise (optional)

        Args:
            audio: Audio chunk (numpy array, float32)
            debug: Print detection metrics

        Returns:
            True if human speech detected, False if silence or ambient noise
        """
        # Ensure model is loaded
        if not self._model_loaded:
            self._load_model()

        # Step 1: Fast RMS pre-filter (reject pure silence)
        self._last_rms = self._calculate_rms(audio)
        if self._last_rms < self.rms_threshold:
            if debug:
                print(f"[VAD] RMS={self._last_rms:.6f} < {self.rms_threshold} → SILENCE")
            return False

        # Step 2: Silero VAD classification (main detector)
        if self._model is not None:
            self._last_silero_prob = self._get_silero_probability(audio)

            # Check Silero threshold
            if self._last_silero_prob < self.silero_threshold:
                if debug:
                    print(f"[VAD] Silero={self._last_silero_prob:.3f} < {self.silero_threshold} → NOISE")
                return False
        else:
            # Fallback: if Silero not available, use RMS only
            if debug:
                print(f"[VAD] Silero indisponible, RMS={self._last_rms:.6f} → ACTIVE")
            return True

        # Step 3: Optional ZCR validation (filter white noise)
        if self.use_zcr_filter:
            self._last_zcr = self._calculate_zcr(audio)

            if not (self.zcr_min <= self._last_zcr <= self.zcr_max):
                if debug:
                    print(f"[VAD] ZCR={self._last_zcr:.4f} hors limites [{self.zcr_min}, {self.zcr_max}] → NOISE")
                return False

        # All checks passed → human speech detected
        if debug:
            print(f"[VAD] ✓ VOIX: RMS={self._last_rms:.6f}, Silero={self._last_silero_prob:.3f}, ZCR={self._last_zcr:.4f}")

        return True

    def get_metrics(self) -> dict[str, float]:
        """
        Get last detection metrics for debugging/tuning.

        Returns:
            Dictionary with RMS, Silero probability, and ZCR
        """
        return {
            "rms": self._last_rms,
            "silero_probability": self._last_silero_prob,
            "zero_crossing_rate": self._last_zcr,
        }

    def unload_model(self) -> None:
        """Unload Silero VAD model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_loaded = False
            print("🗑️ Silero VAD déchargé")
