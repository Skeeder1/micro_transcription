"""Intelligent phrase end detection for better transcription segmentation.

This module detects natural phrase boundaries by combining:
1. Silence detection (pause in speech)
2. Energy drop analysis (falling energy = end of word/phrase)
3. Pitch contour analysis (falling pitch = declarative sentence end)
"""

from __future__ import annotations

from collections import deque
from typing import Optional

import numpy as np

from shared import config


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

    def reset(self) -> None:
        """Reset detector state for new utterance."""
        self._energy_history.clear()
        self._pitch_history.clear()
        self._zcr_history.clear()
        self._peak_energy = 0.0
        self._speech_started = False
        self._silence_count = 0

    def _calculate_rms(self, audio: np.ndarray) -> float:
        """Calculate RMS energy of audio block."""
        return float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))

    def _calculate_zcr(self, audio: np.ndarray) -> float:
        """Calculate Zero Crossing Rate."""
        if len(audio) < 2:
            return 0.0
        signs = np.sign(audio)
        zero_crossings = np.sum(np.abs(np.diff(signs))) / 2.0
        return float(zero_crossings / len(audio))

    def _estimate_pitch(self, audio: np.ndarray) -> Optional[float]:
        """
        Estimate fundamental frequency (F0) using autocorrelation.

        Returns:
            Estimated F0 in Hz, or None if no clear pitch detected
        """
        if len(audio) < 512:
            return None

        # Autocorrelation
        audio_centered = audio - np.mean(audio)
        corr = np.correlate(audio_centered, audio_centered, mode='full')
        corr = corr[len(corr) // 2:]

        # Find first peak after initial dip
        # F0 range: 85-255 Hz (male), 165-255 Hz (female)
        # At 16kHz: 85Hz = 188 samples, 255Hz = 63 samples
        min_lag = int(self.sample_rate / 400)  # 400 Hz max
        max_lag = int(self.sample_rate / 70)   # 70 Hz min

        if max_lag >= len(corr):
            return None

        # Find peak in valid range
        search_range = corr[min_lag:max_lag]
        if len(search_range) == 0:
            return None

        peak_idx = np.argmax(search_range) + min_lag

        # Validate peak (should be significant)
        if corr[peak_idx] < 0.3 * corr[0]:
            return None

        f0 = self.sample_rate / peak_idx
        return f0

    def _detect_energy_drop(self) -> bool:
        """
        Detect significant energy drop indicating end of speech.

        Returns:
            True if energy has dropped significantly from peak
        """
        if len(self._energy_history) < 3:
            return False

        # Current energy vs peak
        current = self._energy_history[-1]

        if self._peak_energy < 1e-10:
            return False

        ratio = current / self._peak_energy

        # Energy dropped below threshold
        return ratio < self.energy_drop_threshold

    def _detect_pitch_drop(self) -> bool:
        """
        Detect falling pitch contour (declarative sentence end).

        Returns:
            True if pitch is falling (indicating statement end)
        """
        if len(self._pitch_history) < 3:
            return False

        # Get valid pitch values (non-None)
        valid_pitches = [p for p in self._pitch_history if p is not None and p > 0]

        if len(valid_pitches) < 2:
            return False

        # Check if pitch is falling
        recent = np.mean(valid_pitches[-2:]) if len(valid_pitches) >= 2 else valid_pitches[-1]
        earlier = np.mean(valid_pitches[:2]) if len(valid_pitches) >= 2 else valid_pitches[0]

        # Pitch drop of >15% indicates falling intonation
        if earlier > 0:
            return (earlier - recent) / earlier > 0.15

        return False

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

        # Track peak energy during speech
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
            # Fallback to simple silence count
            return is_silent and self._silence_count >= config.SILENCE_BLOCKS_BEFORE_FLUSH

        # Must have silence
        if not is_silent:
            return False

        # Must have had speech before
        if not self._speech_started:
            return False

        # Minimum silence required (at least 1 block)
        if self._silence_count < 1:
            return False

        # Check acoustic indicators
        energy_drop = self._detect_energy_drop()
        pitch_drop = self._detect_pitch_drop()

        # Decision logic:
        # - 2+ blocks silence + energy drop = phrase end
        # - 1 block silence + energy drop + pitch drop = phrase end
        # - 3+ blocks silence = phrase end (fallback)

        if self._silence_count >= 3:
            return True

        if self._silence_count >= 2 and energy_drop:
            return True

        if self._silence_count >= 1 and energy_drop and pitch_drop:
            return True

        return False

    def get_confidence(self) -> float:
        """
        Get confidence score for phrase end detection.

        Returns:
            Confidence score 0.0-1.0
        """
        if not self._speech_started:
            return 0.0

        score = 0.0

        # Silence contribution
        silence_score = min(self._silence_count / 3.0, 1.0) * 0.4
        score += silence_score

        # Energy drop contribution
        if self._detect_energy_drop():
            score += 0.35

        # Pitch drop contribution
        if self._detect_pitch_drop():
            score += 0.25

        return min(score, 1.0)

    def get_metrics(self) -> dict[str, float]:
        """
        Get current detection metrics for debugging.

        Returns:
            Dictionary with current metric values
        """
        return {
            "current_energy": self._energy_history[-1] if self._energy_history else 0.0,
            "peak_energy": self._peak_energy,
            "silence_count": float(self._silence_count),
            "energy_drop_detected": 1.0 if self._detect_energy_drop() else 0.0,
            "pitch_drop_detected": 1.0 if self._detect_pitch_drop() else 0.0,
            "confidence": self.get_confidence(),
        }
