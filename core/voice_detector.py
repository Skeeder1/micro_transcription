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
        use_adaptive: bool = True,
        adaptive_boost_factor: float = 2.5,
        adaptive_window_seconds: float = 3.0,
    ):
        """
        Initialize voice detector.

        Args:
            sample_rate: Audio sample rate (must match Silero: 8000 or 16000)
            silero_threshold: Probability threshold for voice (0.0-1.0, default 0.5)
            rms_threshold: Energy threshold for silence rejection (fallback)
            use_zcr_filter: Enable Zero Crossing Rate filtering
            zcr_min: Minimum ZCR for voice (below = likely DC offset or hum)
            zcr_max: Maximum ZCR for voice (above = likely white noise)
            use_adaptive: Enable adaptive detection (detects speech over ambient noise)
            adaptive_boost_factor: Speech must be X times louder than ambient (default 2.5)
            adaptive_window_seconds: Duration of reference window for ambient level
        """
        self.sample_rate = sample_rate
        self.silero_threshold = silero_threshold
        self.rms_threshold = rms_threshold
        self.use_zcr_filter = use_zcr_filter
        self.zcr_min = zcr_min
        self.zcr_max = zcr_max
        self.use_adaptive = use_adaptive
        self.adaptive_boost_factor = adaptive_boost_factor
        self.adaptive_window_seconds = adaptive_window_seconds

        # Lazy-load Silero VAD model
        self._model: Optional[torch.nn.Module] = None
        self._model_loaded = False

        # Cache for performance
        self._last_silero_prob: float = 0.0
        self._last_zcr: float = 0.0
        self._last_rms: float = 0.0
        self._last_boost: float = 0.0

        # Adaptive detection state
        self._rms_history: list[float] = []
        self._reference_rms: float = self.rms_threshold
        self._is_calibrating: bool = True
        self._calibration_count: int = 0
        # Calibration: collect ~4 chunks (2 seconds at 0.5s per chunk)
        self._max_calibration_count: int = 4

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

    def _update_reference_level(self, current_rms: float) -> None:
        """
        Update adaptive reference level (ambient noise baseline).

        Uses exponential moving average to track ambient noise level.
        """
        if not self.use_adaptive:
            return

        # Calibration phase: collect initial chunks
        if self._is_calibrating:
            self._rms_history.append(current_rms)
            self._calibration_count += 1

            if self._calibration_count >= self._max_calibration_count:
                # End calibration: compute initial reference
                if self._rms_history:
                    self._reference_rms = float(np.median(self._rms_history))
                    # Ensure minimum threshold
                    self._reference_rms = max(self._reference_rms, self.rms_threshold)
                self._is_calibrating = False
                print(f"🎯 Calibration terminée: niveau ambiant = {self._reference_rms:.6f}")
            return

        # Normal operation: exponential moving average
        # Only update with "quiet" samples (not speech)
        # If current level is close to reference, it's likely ambient noise
        if current_rms < self._reference_rms * (self.adaptive_boost_factor * 0.7):
            # Slow adaptation (alpha = 0.05 means 5% new, 95% old)
            alpha = 0.05
            self._reference_rms = alpha * current_rms + (1 - alpha) * self._reference_rms
            # Ensure minimum threshold
            self._reference_rms = max(self._reference_rms, self.rms_threshold)

    def _get_boost_factor(self, current_rms: float) -> float:
        """
        Calculate how much louder current audio is vs ambient.

        Returns:
            Boost factor (1.0 = same as ambient, 3.0 = 3x louder)
        """
        if self._reference_rms < 1e-10:
            return 0.0
        return current_rms / self._reference_rms

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

        Pipeline (Adaptive Mode):
        1. Calculate current RMS
        2. Update reference level (ambient baseline)
        3. Check boost factor (current vs reference)
        4. Silero VAD → confirm it's voice
        5. Optional ZCR → filter white noise

        Pipeline (Legacy Mode):
        1. RMS check → reject pure silence
        2. Silero VAD → get ML probability
        3. ZCR check → validate not white noise

        Args:
            audio: Audio chunk (numpy array, float32)
            debug: Print detection metrics

        Returns:
            True if human speech detected, False if silence or ambient noise
        """
        # Ensure model is loaded
        if not self._model_loaded:
            self._load_model()

        # Calculate RMS
        self._last_rms = self._calculate_rms(audio)

        # ADAPTIVE MODE: Detect speech over ambient noise
        if self.use_adaptive:
            # Update reference level with current sample
            self._update_reference_level(self._last_rms)

            # During calibration, reject everything
            if self._is_calibrating:
                if debug:
                    remaining = self._max_calibration_count - self._calibration_count
                    print(f"[VAD] CALIBRATION: {remaining} chunks restants...")
                return False

            # Calculate boost factor
            self._last_boost = self._get_boost_factor(self._last_rms)

            # Step 1: Check if energy boost is significant
            if self._last_boost < self.adaptive_boost_factor:
                if debug:
                    print(f"[VAD] REF={self._reference_rms:.6f} NOW={self._last_rms:.6f} BOOST={self._last_boost:.2f}x < {self.adaptive_boost_factor}x → AMBIANT")
                return False

            # Step 2: Silero VAD confirmation (is it really voice?)
            if self._model is not None:
                self._last_silero_prob = self._get_silero_probability(audio)

                if self._last_silero_prob < self.silero_threshold:
                    if debug:
                        print(f"[VAD] BOOST={self._last_boost:.2f}x OK, mais Silero={self._last_silero_prob:.3f} < {self.silero_threshold} → BRUIT")
                    return False
            else:
                # No Silero, use boost factor only
                if debug:
                    print(f"[VAD] REF={self._reference_rms:.6f} NOW={self._last_rms:.6f} BOOST={self._last_boost:.2f}x → VOIX")
                return True

            # Step 3: Optional ZCR validation
            if self.use_zcr_filter:
                self._last_zcr = self._calculate_zcr(audio)

                if not (self.zcr_min <= self._last_zcr <= self.zcr_max):
                    if debug:
                        print(f"[VAD] BOOST OK, Silero OK, mais ZCR={self._last_zcr:.4f} hors limites → BRUIT")
                    return False

            # All checks passed
            if debug:
                print(f"[VAD] ✓ VOIX: REF={self._reference_rms:.6f} NOW={self._last_rms:.6f} BOOST={self._last_boost:.2f}x Silero={self._last_silero_prob:.3f}")

            return True

        # LEGACY MODE: Simple thresholds
        else:
            # Step 1: Fast RMS pre-filter
            if self._last_rms < self.rms_threshold:
                if debug:
                    print(f"[VAD] RMS={self._last_rms:.6f} < {self.rms_threshold} → SILENCE")
                return False

            # Step 2: Silero VAD
            if self._model is not None:
                self._last_silero_prob = self._get_silero_probability(audio)

                if self._last_silero_prob < self.silero_threshold:
                    if debug:
                        print(f"[VAD] Silero={self._last_silero_prob:.3f} < {self.silero_threshold} → NOISE")
                    return False
            else:
                if debug:
                    print(f"[VAD] Silero indisponible, RMS={self._last_rms:.6f} → ACTIVE")
                return True

            # Step 3: Optional ZCR
            if self.use_zcr_filter:
                self._last_zcr = self._calculate_zcr(audio)

                if not (self.zcr_min <= self._last_zcr <= self.zcr_max):
                    if debug:
                        print(f"[VAD] ZCR={self._last_zcr:.4f} hors limites → NOISE")
                    return False

            # All checks passed
            if debug:
                print(f"[VAD] ✓ VOIX: RMS={self._last_rms:.6f}, Silero={self._last_silero_prob:.3f}, ZCR={self._last_zcr:.4f}")

            return True

    def get_metrics(self) -> dict[str, float]:
        """
        Get last detection metrics for debugging/tuning.

        Returns:
            Dictionary with RMS, Silero probability, ZCR, and adaptive metrics
        """
        return {
            "rms": self._last_rms,
            "silero_probability": self._last_silero_prob,
            "zero_crossing_rate": self._last_zcr,
            "reference_rms": self._reference_rms,
            "boost_factor": self._last_boost,
            "is_calibrating": 1.0 if self._is_calibrating else 0.0,
        }

    def unload_model(self) -> None:
        """Unload Silero VAD model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_loaded = False
            print("🗑️ Silero VAD déchargé")
