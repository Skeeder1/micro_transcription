"""Audio preprocessing for improved transcription quality."""

from __future__ import annotations

import numpy as np

from shared import config

# scipy fournit lfilter (boucle IIR en C). Importe au chargement du module et
# non dans apply_highpass_filter: l'import coute ~800 ms et serait paye en
# plein milieu de la premiere transcription.
try:
    from scipy.signal import lfilter as _lfilter
except ImportError:  # pragma: no cover - depend de l'environnement
    _lfilter = None


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

    Filtre IIR d'ordre 1: y[n] = alpha * (y[n-1] + x[n] - x[n-1]),
    soit b = [alpha, -alpha], a = [1, -alpha].

    L'implementation vectorisee (scipy.signal.lfilter, boucle en C) est
    ~100x plus rapide que la recurrence en Python pur, qui coutait ~150 ms
    par buffer de 30 s a 16 kHz sur le chemin de production. Le fallback
    Python pur est conserve si scipy est absent.

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

    if _lfilter is None:
        # Fallback: recurrence en Python pur (lente mais sans dependance)
        filtered = np.zeros_like(audio)
        filtered[0] = audio[0]
        for i in range(1, len(audio)):
            filtered[i] = alpha * (filtered[i - 1] + audio[i] - audio[i - 1])
        return filtered.astype(audio.dtype)

    # zi choisi pour reproduire exactement la condition initiale y[0] = x[0]:
    #   y[0] = b[0]*x[0] + zi  =>  zi = x[0] * (1 - alpha)
    work = audio.astype(np.float64, copy=False)
    zi = np.array([work[0] * (1.0 - alpha)], dtype=np.float64)
    filtered, _ = _lfilter([alpha, -alpha], [1.0, -alpha], work, zi=zi)

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


def preprocess_audio(
    audio: np.ndarray,
    sample_rate: int = 16000,
    for_production: bool = True
) -> np.ndarray:
    """
    Apply all preprocessing steps to audio.

    Pipeline:
    1. High-pass filter (remove hum and low noise)
    2. Noise reduction (deep learning, if enabled)
    3. Amplification (boost quiet speech)
    4. Normalization (prevent clipping)

    Args:
        audio: Raw audio signal
        sample_rate: Sample rate in Hz
        for_production: True for production (full processing), False for preview (lighter)

    Returns:
        Preprocessed audio ready for Whisper
    """
    # Step 1: High-pass filter (80 Hz cutoff removes 50/60 Hz hum and low rumble)
    audio = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

    # Step 2: Noise reduction (only for production to save latency on preview)
    if for_production and getattr(config, 'ENABLE_NOISE_REDUCTION', False):
        try:
            from .noise_reduction import reduce_noise
            audio = reduce_noise(audio, sample_rate)
        except ImportError as e:
            pass  # Noise reduction not available, continue without it

    # Step 3: Amplify if signal is too quiet
    audio = amplify_audio(audio, target_rms=0.1)

    # Step 4: Normalize to [-1, 1] to prevent clipping
    audio = normalize_audio(audio)

    return audio
