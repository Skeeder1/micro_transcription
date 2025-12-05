"""
Advanced voice activity detection combining Silero VAD and Zero Crossing Rate.

This module provides human speech detection that distinguishes voice from ambient noise,
improving transcription accuracy and end-of-speech detection.
"""

from __future__ import annotations

import os
import time
from typing import Optional, Tuple

import numpy as np
import torch

from shared.audio_utils import calculate_rms, calculate_zcr
from shared.exceptions import ModelLoadError


# =============================================================================
# Constants
# =============================================================================

# Calibration settings
CALIBRATION_CHUNKS = 4  # Number of chunks for initial calibration (~2s at 0.5s/chunk)
RECALIBRATION_SILENCE_THRESHOLD = 30.0  # Recalibrate after 30s of silence

# Silero VAD requirements
SILERO_SAMPLES_16K = 512  # Required samples for 16kHz
SILERO_SAMPLES_8K = 256   # Required samples for 8kHz
SILERO_HOP_RATIO = 0.5    # 50% overlap for sliding window

# Adaptive detection
REFERENCE_UPDATE_ALPHA = 0.05  # EMA alpha for reference level (5% new, 95% old)
AMBIENT_FACTOR_MARGIN = 0.7   # Margin for ambient vs speech classification


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
        self._max_calibration_count: int = CALIBRATION_CHUNKS

        # Recalibration state
        self._seconds_since_last_speech: float = 0.0
        self._last_update_time: float = 0.0
        self._recalibration_threshold: float = RECALIBRATION_SILENCE_THRESHOLD

    # =========================================================================
    # Model Management
    # =========================================================================

    def _load_model(self) -> None:
        """Load Silero VAD model (lazy initialization)."""
        if self._model_loaded:
            return

        try:
            torch.hub.set_dir(
                os.path.join(os.path.dirname(__file__), "..", ".cache", "torch")
            )

            model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False,
            )

            self._model = model
            self._model_loaded = True
            self._model.eval()

            print(
                f"✅ Silero VAD chargé "
                f"(sample_rate={self.sample_rate}, threshold={self.silero_threshold})"
            )

        except Exception as e:
            print(f"⚠️ Échec chargement Silero VAD: {e}")
            print("   → Mode dégradé: utilisation RMS uniquement")
            self._model_loaded = False

    def unload_model(self) -> None:
        """Unload Silero VAD model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            self._model_loaded = False
            print("🗑️ Silero VAD déchargé")

    # =========================================================================
    # Audio Analysis (using shared utilities)
    # =========================================================================

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS energy (delegating to shared utility)."""
        return calculate_rms(audio)

    def _calculate_zcr(self, audio: np.ndarray) -> float:
        """Calculate Zero Crossing Rate (delegating to shared utility)."""
        return calculate_zcr(audio)

    # =========================================================================
    # Adaptive Detection Helpers
    # =========================================================================

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
                self._complete_calibration()
            return

        # Normal operation: EMA update with quiet samples only
        if current_rms < self._reference_rms * (self.adaptive_boost_factor * AMBIENT_FACTOR_MARGIN):
            self._reference_rms = (
                REFERENCE_UPDATE_ALPHA * current_rms +
                (1 - REFERENCE_UPDATE_ALPHA) * self._reference_rms
            )
            self._reference_rms = max(self._reference_rms, self.rms_threshold)

    def _complete_calibration(self) -> None:
        """Complete calibration phase and set initial reference level."""
        if self._rms_history:
            self._reference_rms = float(np.median(self._rms_history))
            self._reference_rms = max(self._reference_rms, self.rms_threshold)
        self._is_calibrating = False
        print(f"🎯 Calibration terminée: niveau ambiant = {self._reference_rms:.6f}")

    def _get_boost_factor(self, current_rms: float) -> float:
        """Calculate how much louder current audio is vs ambient."""
        if self._reference_rms < 1e-10:
            return 0.0
        return current_rms / self._reference_rms

    # =========================================================================
    # Silero VAD
    # =========================================================================

    def _get_silero_probability(self, audio: np.ndarray) -> float:
        """Get voice probability from Silero VAD (single window)."""
        if self._model is None:
            return 0.0

        try:
            required_samples = SILERO_SAMPLES_16K if self.sample_rate == 16000 else SILERO_SAMPLES_8K
            audio = self._prepare_audio_for_silero(audio, required_samples)

            if len(audio) == required_samples:
                audio_tensor = torch.from_numpy(audio).float()
                with torch.no_grad():
                    return float(self._model(audio_tensor, self.sample_rate).item())

            # Multiple windows - return max probability
            return self._process_multiple_windows(audio, required_samples)

        except Exception as e:
            print(f"⚠️ Erreur Silero VAD: {e}")
            return 0.0

    def _get_silero_probability_voting(self, audio: np.ndarray) -> Tuple[float, bool]:
        """
        Get voice probability using sliding window with majority voting.

        More robust than simple MAX - reduces false positives from noise spikes.

        Returns:
            Tuple of (average probability, is_voice based on voting)
        """
        if self._model is None:
            return 0.0, False

        try:
            required_samples = SILERO_SAMPLES_16K if self.sample_rate == 16000 else SILERO_SAMPLES_8K
            hop_size = int(required_samples * SILERO_HOP_RATIO)

            audio = self._prepare_audio_for_silero(audio, required_samples)

            if len(audio) < required_samples:
                prob = self._model(torch.from_numpy(audio).float(), self.sample_rate).item()
                return prob, prob > self.silero_threshold

            # Sliding window analysis
            probabilities, votes = self._analyze_sliding_windows(
                audio, required_samples, hop_size
            )

            if not probabilities:
                return 0.0, False

            avg_prob = float(np.mean(probabilities))
            vote_ratio = sum(votes) / len(votes)
            is_voice = vote_ratio > 0.5

            return avg_prob, is_voice

        except Exception as e:
            print(f"⚠️ Erreur Silero VAD voting: {e}")
            return 0.0, False

    def _prepare_audio_for_silero(
        self, audio: np.ndarray, required_samples: int
    ) -> np.ndarray:
        """Prepare audio array for Silero VAD input."""
        if audio.ndim > 1:
            audio = audio.squeeze()

        if len(audio) < required_samples:
            audio = np.pad(audio, (0, required_samples - len(audio)), mode='constant')

        return audio

    def _process_multiple_windows(
        self, audio: np.ndarray, required_samples: int
    ) -> float:
        """Process audio with multiple non-overlapping windows."""
        num_windows = len(audio) // required_samples
        probabilities = []

        for i in range(num_windows):
            start = i * required_samples
            chunk = audio[start:start + required_samples]
            audio_tensor = torch.from_numpy(chunk).float()

            with torch.no_grad():
                prob = self._model(audio_tensor, self.sample_rate).item()
                probabilities.append(prob)

        return float(max(probabilities)) if probabilities else 0.0

    def _analyze_sliding_windows(
        self,
        audio: np.ndarray,
        window_size: int,
        hop_size: int
    ) -> Tuple[list, list]:
        """Analyze audio with sliding windows for voting."""
        probabilities = []
        votes = []

        for start in range(0, len(audio) - window_size + 1, hop_size):
            chunk = audio[start:start + window_size]
            audio_tensor = torch.from_numpy(chunk).float()

            with torch.no_grad():
                prob = self._model(audio_tensor, self.sample_rate).item()
                probabilities.append(prob)
                votes.append(prob > self.silero_threshold)

        return probabilities, votes

    # =========================================================================
    # Recalibration
    # =========================================================================

    def _check_recalibration(self, is_speech: bool) -> None:
        """Check if recalibration is needed and trigger it if necessary."""
        current_time = time.time()

        if self._last_update_time == 0:
            self._last_update_time = current_time
            return

        elapsed = current_time - self._last_update_time
        self._last_update_time = current_time

        if is_speech:
            self._seconds_since_last_speech = 0.0
        else:
            self._seconds_since_last_speech += elapsed
            if self._seconds_since_last_speech >= self._recalibration_threshold:
                self._trigger_recalibration()

    def _trigger_recalibration(self) -> None:
        """Reset calibration state to recalibrate ambient noise level."""
        self._is_calibrating = True
        self._calibration_count = 0
        self._rms_history.clear()
        self._seconds_since_last_speech = 0.0
        print("🔄 Recalibration automatique du bruit ambiant...")

    # =========================================================================
    # Main Detection Logic (refactored into sub-methods)
    # =========================================================================

    def is_human_speech(self, audio: np.ndarray, debug: bool = False) -> bool:
        """
        Detect if audio contains human speech vs ambient noise.

        Args:
            audio: Audio chunk (numpy array, float32)
            debug: Print detection metrics

        Returns:
            True if human speech detected, False if silence or ambient noise
        """
        if not self._model_loaded:
            self._load_model()

        self._last_rms = self._calculate_rms(audio)

        if self.use_adaptive:
            return self._detect_adaptive(audio, debug)
        else:
            return self._detect_legacy(audio, debug)

    def _detect_adaptive(self, audio: np.ndarray, debug: bool) -> bool:
        """
        Adaptive detection mode: detect speech over ambient noise.

        Steps:
        1. Update reference level
        2. Check if calibrating
        3. Check boost factor
        4. Silero VAD confirmation
        5. Optional ZCR validation
        """
        self._update_reference_level(self._last_rms)

        # During calibration, reject everything
        if self._is_calibrating:
            if debug:
                remaining = self._max_calibration_count - self._calibration_count
                print(f"[VAD] CALIBRATION: {remaining} chunks restants...")
            return False

        # Step 1: Check energy boost
        self._last_boost = self._get_boost_factor(self._last_rms)
        if not self._check_boost_threshold(debug):
            return False

        # Step 2: Silero VAD confirmation
        if not self._check_silero_adaptive(audio, debug):
            return False

        # Step 3: ZCR validation
        if not self._check_zcr_filter(audio, debug):
            return False

        # All checks passed
        if debug:
            print(
                f"[VAD] ✓ VOIX: REF={self._reference_rms:.6f} "
                f"NOW={self._last_rms:.6f} BOOST={self._last_boost:.2f}x "
                f"Silero={self._last_silero_prob:.3f}"
            )

        self._check_recalibration(True)
        return True

    def _detect_legacy(self, audio: np.ndarray, debug: bool) -> bool:
        """
        Legacy detection mode: simple thresholds.

        Steps:
        1. RMS pre-filter
        2. Silero VAD
        3. Optional ZCR validation
        """
        # Step 1: RMS pre-filter
        if self._last_rms < self.rms_threshold:
            if debug:
                print(f"[VAD] RMS={self._last_rms:.6f} < {self.rms_threshold} → SILENCE")
            return False

        # Step 2: Silero VAD
        if not self._check_silero_legacy(audio, debug):
            return False

        # Step 3: ZCR validation
        if not self._check_zcr_filter(audio, debug):
            return False

        # All checks passed
        if debug:
            print(
                f"[VAD] ✓ VOIX: RMS={self._last_rms:.6f}, "
                f"Silero={self._last_silero_prob:.3f}, ZCR={self._last_zcr:.4f}"
            )

        self._check_recalibration(True)
        return True

    def _check_boost_threshold(self, debug: bool) -> bool:
        """Check if energy boost meets threshold (adaptive mode)."""
        if self._last_boost < self.adaptive_boost_factor:
            if debug:
                print(
                    f"[VAD] REF={self._reference_rms:.6f} NOW={self._last_rms:.6f} "
                    f"BOOST={self._last_boost:.2f}x < {self.adaptive_boost_factor}x → AMBIANT"
                )
            return False
        return True

    def _check_silero_adaptive(self, audio: np.ndarray, debug: bool) -> bool:
        """Check Silero VAD with voting (adaptive mode)."""
        if self._model is None:
            if debug:
                print(
                    f"[VAD] REF={self._reference_rms:.6f} NOW={self._last_rms:.6f} "
                    f"BOOST={self._last_boost:.2f}x → VOIX"
                )
            return True

        self._last_silero_prob, is_voice = self._get_silero_probability_voting(audio)

        if not is_voice:
            if debug:
                print(
                    f"[VAD] BOOST={self._last_boost:.2f}x OK, "
                    f"mais Silero vote={self._last_silero_prob:.3f} → BRUIT"
                )
            self._check_recalibration(False)
            return False

        return True

    def _check_silero_legacy(self, audio: np.ndarray, debug: bool) -> bool:
        """Check Silero VAD with simple threshold (legacy mode)."""
        if self._model is None:
            if debug:
                print(f"[VAD] Silero indisponible, RMS={self._last_rms:.6f} → ACTIVE")
            return True

        self._last_silero_prob = self._get_silero_probability(audio)

        if self._last_silero_prob < self.silero_threshold:
            if debug:
                print(
                    f"[VAD] Silero={self._last_silero_prob:.3f} "
                    f"< {self.silero_threshold} → NOISE"
                )
            return False

        return True

    def _check_zcr_filter(self, audio: np.ndarray, debug: bool) -> bool:
        """Check ZCR is within voice range."""
        if not self.use_zcr_filter:
            return True

        self._last_zcr = self._calculate_zcr(audio)

        if not (self.zcr_min <= self._last_zcr <= self.zcr_max):
            if debug:
                print(f"[VAD] ZCR={self._last_zcr:.4f} hors limites → BRUIT")
            return False

        return True

    # =========================================================================
    # Metrics
    # =========================================================================

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
            "seconds_since_speech": self._seconds_since_last_speech,
        }
