"""
Intelligent phrase end detection for better transcription segmentation.

This module detects natural phrase boundaries by combining:
1. Silence detection (pause in speech)
2. Energy drop analysis (falling energy = end of word/phrase)
3. Pitch contour analysis (falling pitch = declarative sentence end)
"""

from __future__ import annotations

from collections import deque
from typing import Optional, Dict, Any

import numpy as np

from shared import config
from shared.audio_utils import calculate_rms, calculate_zcr, estimate_pitch_autocorr
from shared.constants import (
    SPEECH_F0_MIN,
    SPEECH_F0_MAX,
    PITCH_DROP_THRESHOLD,
    MIN_AUDIO_SAMPLES_FOR_PITCH,
    ENERGY_EPSILON,
    SILENCE_BLOCKS_DEFINITE,
    SILENCE_BLOCKS_WITH_ENERGY,
    SILENCE_BLOCKS_WITH_PITCH,
)


class PhraseEndDetector:
    """
    Detects end of phrases using multiple acoustic features.

    Combines silence detection with prosodic analysis for more
    natural phrase segmentation than simple silence threshold.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        history_size: int = 5,
        energy_drop_threshold: float = 0.3,
    ):
        """
        Initialize phrase end detector.

        Args:
            sample_rate: Audio sample rate in Hz
            history_size: Number of audio blocks to keep in history
            energy_drop_threshold: Threshold for energy drop detection (0.0-1.0)
                                   0.3 = 70% drop from peak
        """
        self.sample_rate = sample_rate
        self.history_size = history_size
        self.energy_drop_threshold = energy_drop_threshold

        # History buffers
        self._energy_history: deque[float] = deque(maxlen=history_size)
        self._pitch_history: deque[float] = deque(maxlen=history_size)
        self._zcr_history: deque[float] = deque(maxlen=history_size)

        # State tracking
        self._peak_energy: float = 0.0
        self._speech_started: bool = False
        self._silence_count: int = 0

    # =========================================================================
    # State Management
    # =========================================================================

    def reset(self) -> None:
        """Reset detector state for new utterance."""
        self._energy_history.clear()
        self._pitch_history.clear()
        self._zcr_history.clear()
        self._peak_energy = 0.0
        self._speech_started = False
        self._silence_count = 0

    # =========================================================================
    # Audio Analysis (using shared utilities)
    # =========================================================================

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS energy (delegating to shared utility)."""
        return calculate_rms(audio)

    def _calculate_zcr(self, audio: np.ndarray) -> float:
        """Calculate Zero Crossing Rate (delegating to shared utility)."""
        return calculate_zcr(audio)

    def _estimate_pitch(self, audio: np.ndarray) -> Optional[float]:
        """
        Estimate fundamental frequency (F0) using autocorrelation.

        Returns:
            Estimated F0 in Hz, or None if no clear pitch detected
        """
        if len(audio) < MIN_AUDIO_SAMPLES_FOR_PITCH:
            return None

        return estimate_pitch_autocorr(
            audio,
            self.sample_rate,
            f0_min=SPEECH_F0_MIN,
            f0_max=SPEECH_F0_MAX
        )

    # =========================================================================
    # Feature Detection
    # =========================================================================

    def _detect_energy_drop(self) -> bool:
        """
        Detect significant energy drop indicating end of speech.

        Returns:
            True if energy has dropped significantly from peak
        """
        if len(self._energy_history) < 3:
            return False

        current = self._energy_history[-1]

        if self._peak_energy < ENERGY_EPSILON:
            return False

        ratio = current / self._peak_energy
        return ratio < self.energy_drop_threshold

    def _detect_pitch_drop(self) -> bool:
        """
        Detect falling pitch contour (declarative sentence end).

        Returns:
            True if pitch is falling (indicating statement end)
        """
        if len(self._pitch_history) < 3:
            return False

        valid_pitches = [p for p in self._pitch_history if p is not None and p > 0]

        if len(valid_pitches) < 2:
            return False

        recent = self._get_recent_pitch_average(valid_pitches)
        earlier = self._get_earlier_pitch_average(valid_pitches)

        if earlier > 0:
            return (earlier - recent) / earlier > PITCH_DROP_THRESHOLD

        return False

    def _get_recent_pitch_average(self, pitches: list) -> float:
        """Get average of recent pitch values."""
        if len(pitches) >= 2:
            return float(np.mean(pitches[-2:]))
        return pitches[-1] if pitches else 0.0

    def _get_earlier_pitch_average(self, pitches: list) -> float:
        """Get average of earlier pitch values."""
        if len(pitches) >= 2:
            return float(np.mean(pitches[:2]))
        return pitches[0] if pitches else 0.0

    # =========================================================================
    # Main Detection Logic
    # =========================================================================

    def update(self, audio_block: np.ndarray, is_silent: bool) -> None:
        """
        Update detector with new audio block.

        Args:
            audio_block: New audio samples
            is_silent: Whether VAD detected silence
        """
        # Calculate features
        energy = self._calculate_rms(audio_block)
        zcr = self._calculate_zcr(audio_block)
        pitch = self._estimate_pitch(audio_block)

        # Update history
        self._energy_history.append(energy)
        self._zcr_history.append(zcr)
        if pitch is not None:
            self._pitch_history.append(pitch)

        # Update state
        self._update_speech_state(energy, is_silent)

    def _update_speech_state(self, energy: float, is_silent: bool) -> None:
        """Update speech tracking state."""
        if not is_silent:
            self._speech_started = True
            if energy > self._peak_energy:
                self._peak_energy = energy
            self._silence_count = 0
        else:
            self._silence_count += 1

    def is_phrase_end(self, is_silent: bool) -> bool:
        """
        Determine if current position is end of phrase.

        Combines multiple indicators:
        1. Silence detected by VAD (required)
        2. Energy drop from peak (supporting evidence)
        3. Falling pitch contour (optional supporting evidence)

        Args:
            is_silent: Whether VAD detected silence

        Returns:
            True if this appears to be end of phrase
        """
        if not getattr(config, 'ENABLE_PHRASE_DETECTION', True):
            return self._fallback_detection(is_silent)

        # Must have silence
        if not is_silent:
            return False

        # Must have had speech before
        if not self._speech_started:
            return False

        # Minimum silence required
        if self._silence_count < 1:
            return False

        return self._evaluate_phrase_end()

    def _fallback_detection(self, is_silent: bool) -> bool:
        """Fallback to simple silence count when phrase detection disabled."""
        return is_silent and self._silence_count >= config.SILENCE_BLOCKS_BEFORE_FLUSH

    def _evaluate_phrase_end(self) -> bool:
        """
        Evaluate phrase end using acoustic indicators.

        Decision logic:
        - 3+ blocks silence = phrase end (definite)
        - 2+ blocks silence + energy drop = phrase end
        - 1+ block silence + energy drop + pitch drop = phrase end
        """
        energy_drop = self._detect_energy_drop()
        pitch_drop = self._detect_pitch_drop()

        # Definite phrase end after enough silence
        if self._silence_count >= SILENCE_BLOCKS_DEFINITE:
            return True

        # Phrase end with energy drop
        if self._silence_count >= SILENCE_BLOCKS_WITH_ENERGY and energy_drop:
            return True

        # Phrase end with both energy and pitch drop
        if self._silence_count >= SILENCE_BLOCKS_WITH_PITCH and energy_drop and pitch_drop:
            return True

        return False

    # =========================================================================
    # Metrics
    # =========================================================================

    def get_confidence(self) -> float:
        """
        Get confidence score for phrase end detection.

        Returns:
            Confidence score 0.0-1.0
        """
        if not self._speech_started:
            return 0.0

        score = 0.0

        # Silence contribution (40% max)
        silence_score = min(self._silence_count / 3.0, 1.0) * 0.4
        score += silence_score

        # Energy drop contribution (35%)
        if self._detect_energy_drop():
            score += 0.35

        # Pitch drop contribution (25%)
        if self._detect_pitch_drop():
            score += 0.25

        return min(score, 1.0)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current detection metrics for debugging.

        Returns:
            Dictionary with current metric values
        """
        return {
            "current_energy": self._energy_history[-1] if self._energy_history else 0.0,
            "peak_energy": self._peak_energy,
            "silence_count": float(self._silence_count),
            "speech_started": self._speech_started,
            "energy_drop_detected": self._detect_energy_drop(),
            "pitch_drop_detected": self._detect_pitch_drop(),
            "confidence": self.get_confidence(),
        }
