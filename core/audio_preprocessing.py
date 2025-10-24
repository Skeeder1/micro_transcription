"""Audio preprocessing for improved transcription quality."""

from __future__ import annotations

import numpy as np


def normalize_audio(audio: np.ndarray) -> np.ndarray:
    """
    Normalize audio to [-1, 1] range.

    Prevents clipping and improves model performance.
    """
    if audio.size == 0:
        return audio

    # Get absolute maximum value
    max_val = np.abs(audio).max()

    # Avoid division by zero
    if max_val == 0:
        return audio

    return audio / max_val


def apply_highpass_filter(audio: np.ndarray, sample_rate: int = 16000, cutoff_hz: float = 80.0) -> np.ndarray:
    """
    Apply simple high-pass filter to remove low-frequency noise and hum.

    Uses a first-order IIR high-pass filter (no scipy dependency).

    Args:
        audio: Audio signal (numpy array)
        sample_rate: Sample rate in Hz (default 16000 for Whisper)
        cutoff_hz: Cutoff frequency in Hz (default 80 Hz removes hum + low noise)

    Returns:
        Filtered audio signal
    """
    if audio.size == 0:
        return audio

    # Calculate filter coefficient (first-order IIR)
    # alpha = cutoff / (cutoff + sample_rate/(2*pi))
    import math
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / sample_rate
    alpha = rc / (rc + dt)

    # Apply first-order high-pass IIR filter (numerically stable)
    # y[n] = alpha * (y[n-1] + x[n] - x[n-1])
    filtered = np.zeros_like(audio)
    filtered[0] = audio[0]

    for i in range(1, len(audio)):
        filtered[i] = alpha * (filtered[i - 1] + audio[i] - audio[i - 1])

    return filtered.astype(audio.dtype)


def amplify_audio(audio: np.ndarray, target_rms: float = 0.1) -> np.ndarray:
    """
    Intelligently amplify quiet audio while preserving dynamics.

    Args:
        audio: Audio signal
        target_rms: Target RMS level (default 0.1)

    Returns:
        Amplified audio signal
    """
    if audio.size == 0:
        return audio

    # Calculate current RMS
    current_rms = np.sqrt(np.mean(np.square(audio)))

    # Avoid division by zero
    if current_rms < 1e-10:
        return audio

    # Calculate gain needed
    gain = target_rms / current_rms

    # Limit gain to prevent over-amplification (max 6dB = 2x)
    gain = min(gain, 2.0)

    return audio * gain


def preprocess_audio(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """
    Apply all preprocessing steps to audio.

    Pipeline:
    1. High-pass filter (remove hum and low noise)
    2. Amplification (boost quiet speech)
    3. Normalization (prevent clipping)

    Args:
        audio: Raw audio signal
        sample_rate: Sample rate in Hz

    Returns:
        Preprocessed audio ready for Whisper
    """
    # Step 1: High-pass filter (80 Hz cutoff removes 50/60 Hz hum and low rumble)
    audio = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

    # Step 2: Amplify if signal is too quiet
    audio = amplify_audio(audio, target_rms=0.1)

    # Step 3: Normalize to [-1, 1] to prevent clipping
    audio = normalize_audio(audio)

    return audio
