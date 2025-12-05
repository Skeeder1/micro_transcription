"""
Shared audio utility functions.

Centralizes common audio calculations used across multiple modules
to avoid code duplication and ensure consistent behavior.
"""

import numpy as np
from typing import Optional


def calculate_rms(audio: np.ndarray) -> float:
    """
    Calculate Root Mean Square (RMS) energy of audio signal.

    RMS is a measure of the average energy in the audio signal,
    commonly used for voice activity detection.

    Args:
        audio: Audio samples as numpy array (any dtype, will be converted)

    Returns:
        RMS value as float. Returns 0.0 for empty arrays.
    """
    if audio is None or len(audio) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio), dtype=np.float64)))


def calculate_zcr(audio: np.ndarray) -> float:
    """
    Calculate Zero Crossing Rate (ZCR) of audio signal.

    ZCR measures how often the signal crosses the zero amplitude line.
    Speech typically has ZCR in range 0.02-0.30, while noise tends to
    have higher ZCR (random crossings) or very low ZCR (constant hum).

    Args:
        audio: Audio samples as numpy array

    Returns:
        ZCR as float in range [0, 1]. Returns 0.0 for arrays < 2 samples.
    """
    if audio is None or len(audio) < 2:
        return 0.0
    # Ensure 1D
    if audio.ndim > 1:
        audio = audio.squeeze()
    signs = np.sign(audio)
    zero_crossings = np.sum(np.abs(np.diff(signs))) / 2.0
    return float(zero_crossings / len(audio))


def validate_audio(
    audio: np.ndarray,
    min_length: int = 512,
    max_length: Optional[int] = None,
    target_dtype: np.dtype = np.float32,
) -> np.ndarray:
    """
    Validate and normalize audio array.

    Ensures audio has correct shape, dtype, and length for processing.

    Args:
        audio: Input audio array
        min_length: Minimum required length (will pad with zeros if shorter)
        max_length: Maximum length (will truncate if longer)
        target_dtype: Target dtype for output

    Returns:
        Validated and normalized audio array

    Raises:
        TypeError: If audio is not a numpy array
        ValueError: If audio is None or empty
    """
    if audio is None:
        raise ValueError("audio cannot be None")

    if not isinstance(audio, np.ndarray):
        raise TypeError(f"audio must be np.ndarray, got {type(audio)}")

    # Squeeze multi-dimensional arrays to 1D
    if audio.ndim > 1:
        audio = audio.squeeze()

    if audio.size == 0:
        raise ValueError("audio cannot be empty")

    # Pad if too short
    if len(audio) < min_length:
        audio = np.pad(audio, (0, min_length - len(audio)))

    # Truncate if too long
    if max_length is not None and len(audio) > max_length:
        audio = audio[:max_length]

    # Convert dtype
    if audio.dtype != target_dtype:
        audio = audio.astype(target_dtype)

    return audio


def normalize_audio(audio: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """
    Normalize audio to target peak level.

    Args:
        audio: Input audio array
        target_peak: Target peak amplitude (0.0-1.0)

    Returns:
        Normalized audio array
    """
    if audio is None or len(audio) == 0:
        return audio

    peak = np.abs(audio).max()
    if peak > 0:
        audio = audio * (target_peak / peak)

    return audio


def audio_to_mono(audio: np.ndarray) -> np.ndarray:
    """
    Convert stereo audio to mono by averaging channels.

    Args:
        audio: Input audio (1D or 2D array)

    Returns:
        Mono audio as 1D array
    """
    if audio.ndim == 1:
        return audio
    elif audio.ndim == 2:
        if audio.shape[0] == 2:
            # Shape is (2, samples) - channels first
            return audio.mean(axis=0).astype(audio.dtype)
        elif audio.shape[1] == 2:
            # Shape is (samples, 2) - channels last
            return audio.mean(axis=1).astype(audio.dtype)
    return audio.squeeze()


def estimate_pitch_autocorr(
    audio: np.ndarray,
    sample_rate: int,
    f0_min: float = 70.0,
    f0_max: float = 400.0,
) -> Optional[float]:
    """
    Estimate fundamental frequency (pitch) using autocorrelation.

    Uses autocorrelation method to find the dominant pitch frequency.
    Works well for voiced speech but may return None for unvoiced sounds.

    Args:
        audio: Audio samples
        sample_rate: Sample rate in Hz
        f0_min: Minimum expected pitch (Hz) - typically 70Hz for male voices
        f0_max: Maximum expected pitch (Hz) - typically 400Hz for female voices

    Returns:
        Estimated pitch in Hz, or None if no clear pitch detected
    """
    if audio is None or len(audio) < sample_rate // int(f0_min):
        return None

    # Ensure audio is 1D (squeeze multi-dimensional arrays)
    if audio.ndim > 1:
        audio = audio.squeeze()
    if audio.ndim != 1:
        return None

    # Calculate lag range from frequency range
    min_lag = int(sample_rate / f0_max)
    max_lag = int(sample_rate / f0_min)

    if max_lag >= len(audio):
        max_lag = len(audio) - 1

    if min_lag >= max_lag:
        return None

    # Compute autocorrelation
    audio_centered = audio - np.mean(audio)
    corr = np.correlate(audio_centered, audio_centered, mode='full')
    corr = corr[len(corr) // 2:]  # Take positive lags only

    # Find peak in valid range
    search_region = corr[min_lag:max_lag]
    if len(search_region) == 0:
        return None

    peak_idx = np.argmax(search_region) + min_lag

    # Validate peak strength (should be at least 30% of zero-lag)
    if corr[peak_idx] < 0.3 * corr[0]:
        return None

    # Convert lag to frequency
    pitch = sample_rate / peak_idx
    return float(pitch)


# Constants for audio analysis
SPEECH_ZCR_MIN = 0.02  # Minimum ZCR for typical speech
SPEECH_ZCR_MAX = 0.30  # Maximum ZCR for typical speech
SPEECH_F0_MIN = 70.0   # Minimum fundamental frequency (Hz)
SPEECH_F0_MAX = 400.0  # Maximum fundamental frequency (Hz)
