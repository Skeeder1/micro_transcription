"""Advanced noise reduction for improved transcription quality.

This module provides multiple noise reduction techniques:
1. Spectral Subtraction: Fast, low-latency, good for stationary noise
2. Deep Learning (noisereduce): Best quality, handles non-stationary noise
3. Hybrid: Combines both for optimal results
"""

from __future__ import annotations

import numpy as np
from typing import Optional

from shared import config


def spectral_subtraction(
    audio: np.ndarray,
    sample_rate: int = 16000,
    noise_frames: int = 10,
    subtraction_factor: float = 1.5,
    floor_factor: float = 0.1
) -> np.ndarray:
    """
    Reduce noise using spectral subtraction.

    Fast method suitable for stationary noise (fans, AC, hum).

    Args:
        audio: Audio signal (numpy array, float32)
        sample_rate: Sample rate in Hz
        noise_frames: Number of initial frames to estimate noise spectrum
        subtraction_factor: How aggressively to subtract noise (1.0-2.0)
        floor_factor: Minimum spectral floor to prevent musical noise

    Returns:
        Noise-reduced audio signal
    """
    if audio.size == 0:
        return audio

    try:
        from scipy.signal import stft, istft
    except ImportError:
        print("Warning: scipy not installed, skipping spectral subtraction")
        return audio

    # STFT parameters
    nperseg = 512  # ~32ms at 16kHz
    noverlap = 384  # 75% overlap

    # Compute STFT
    f, t, Zxx = stft(audio, fs=sample_rate, nperseg=nperseg, noverlap=noverlap)

    # Estimate noise spectrum from first few frames
    if t.shape[0] < noise_frames:
        noise_frames = max(1, t.shape[0] // 2)

    noise_spectrum = np.mean(np.abs(Zxx[:, :noise_frames]), axis=1, keepdims=True)

    # Spectral subtraction with flooring
    magnitude = np.abs(Zxx)
    phase = np.angle(Zxx)

    # Subtract noise spectrum, keeping a floor to avoid musical noise
    magnitude_clean = np.maximum(
        magnitude - noise_spectrum * subtraction_factor,
        floor_factor * magnitude
    )

    # Reconstruct complex spectrum
    Zxx_clean = magnitude_clean * np.exp(1j * phase)

    # Inverse STFT
    _, audio_clean = istft(Zxx_clean, fs=sample_rate, nperseg=nperseg, noverlap=noverlap)

    # Match original length
    if len(audio_clean) > len(audio):
        audio_clean = audio_clean[:len(audio)]
    elif len(audio_clean) < len(audio):
        audio_clean = np.pad(audio_clean, (0, len(audio) - len(audio_clean)))

    return audio_clean.astype(np.float32)


def deep_learning_denoise(
    audio: np.ndarray,
    sample_rate: int = 16000,
    strength: float = 0.75,
    stationary: bool = False
) -> np.ndarray:
    """
    Reduce noise using deep learning (noisereduce library).

    Best quality, handles non-stationary noise like TV, conversations.

    Args:
        audio: Audio signal (numpy array, float32)
        sample_rate: Sample rate in Hz
        strength: Noise reduction strength (0.0-1.0)
        stationary: True for constant noise (fan), False for variable (TV)

    Returns:
        Noise-reduced audio signal
    """
    if audio.size == 0:
        return audio

    try:
        import noisereduce as nr
    except ImportError:
        print("Warning: noisereduce not installed, skipping deep learning denoise")
        return audio

    try:
        # noisereduce with optimized parameters
        audio_clean = nr.reduce_noise(
            y=audio,
            sr=sample_rate,
            stationary=stationary,
            prop_decrease=strength,
            n_fft=512,
            hop_length=128,
            time_constant_s=2.0,  # Smoothing for noise estimation
            freq_mask_smooth_hz=500,  # Frequency smoothing
            time_mask_smooth_ms=50,  # Time smoothing
        )
        return audio_clean.astype(np.float32)
    except Exception as e:
        print(f"Warning: noisereduce failed: {e}")
        return audio


def bandpass_voice_filter(
    audio: np.ndarray,
    sample_rate: int = 16000,
    low_freq: float = 100.0,
    high_freq: float = 8000.0
) -> np.ndarray:
    """
    Apply bandpass filter to keep only voice frequencies.

    Human voice fundamental frequency: 85-255 Hz (male), 165-255 Hz (female)
    With harmonics and consonants: 100-8000 Hz covers speech well.

    Args:
        audio: Audio signal
        sample_rate: Sample rate in Hz
        low_freq: Low cutoff frequency (Hz)
        high_freq: High cutoff frequency (Hz)

    Returns:
        Bandpass filtered audio
    """
    if audio.size == 0:
        return audio

    try:
        from scipy.signal import butter, filtfilt
    except ImportError:
        print("Warning: scipy not installed, skipping bandpass filter")
        return audio

    nyquist = sample_rate / 2
    low = low_freq / nyquist
    high = high_freq / nyquist

    # Ensure valid frequency range
    low = max(0.001, min(low, 0.99))
    high = max(low + 0.01, min(high, 0.99))

    # 4th order Butterworth bandpass
    b, a = butter(4, [low, high], btype='band')

    try:
        audio_filtered = filtfilt(b, a, audio)
        return audio_filtered.astype(np.float32)
    except Exception:
        return audio


def estimate_voice_distance(
    audio: np.ndarray,
    sample_rate: int = 16000
) -> str:
    """
    Estimate if voice is close (<50cm) or far (>1m) based on frequency content.

    Close voices have more low frequencies (proximity effect).

    Args:
        audio: Audio signal
        sample_rate: Sample rate in Hz

    Returns:
        "close" (<50cm), "medium" (50cm-1m), or "far" (>1m)
    """
    if audio.size == 0:
        return "unknown"

    try:
        from scipy.signal import butter, filtfilt
    except ImportError:
        return "unknown"

    nyquist = sample_rate / 2

    # Low frequency energy (< 300 Hz)
    b_low, a_low = butter(4, 300 / nyquist, btype='low')
    low_energy = np.mean(filtfilt(b_low, a_low, audio) ** 2)

    # High frequency energy (> 2000 Hz)
    b_high, a_high = butter(4, 2000 / nyquist, btype='high')
    high_energy = np.mean(filtfilt(b_high, a_high, audio) ** 2)

    # Ratio determines distance
    if high_energy < 1e-10:
        return "unknown"

    ratio = low_energy / high_energy

    if ratio > 5.0:
        return "close"  # < 50cm, strong proximity effect
    elif ratio > 2.0:
        return "medium"  # 50cm - 1m
    else:
        return "far"  # > 1m


def reduce_noise(
    audio: np.ndarray,
    sample_rate: int = 16000,
    noise_profile: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Main noise reduction function using configured method.

    Applies noise reduction based on config settings:
    - ENABLE_NOISE_REDUCTION: Master switch
    - NOISE_REDUCTION_STRENGTH: Intensity (0.0-1.0)
    - NOISE_STATIONARY: Type of noise expected

    Args:
        audio: Audio signal (numpy array, float32)
        sample_rate: Sample rate in Hz
        noise_profile: Optional pre-recorded noise sample for better estimation

    Returns:
        Noise-reduced audio signal
    """
    if not getattr(config, 'ENABLE_NOISE_REDUCTION', False):
        return audio

    if audio.size == 0:
        return audio

    strength = getattr(config, 'NOISE_REDUCTION_STRENGTH', 0.75)
    stationary = getattr(config, 'NOISE_STATIONARY', False)

    # Step 1: Bandpass filter to focus on voice frequencies
    audio = bandpass_voice_filter(audio, sample_rate, low_freq=100.0, high_freq=8000.0)

    # Step 2: Deep learning noise reduction (best quality)
    audio = deep_learning_denoise(
        audio,
        sample_rate=sample_rate,
        strength=strength,
        stationary=stationary
    )

    return audio


class NoiseProfiler:
    """
    Builds and maintains a noise profile for better noise reduction.

    Collects samples during silence periods to characterize ambient noise.
    """

    def __init__(self, sample_rate: int = 16000, profile_seconds: float = 2.0):
        self.sample_rate = sample_rate
        self.profile_seconds = profile_seconds
        self.max_samples = int(sample_rate * profile_seconds)
        self.noise_samples: list[np.ndarray] = []
        self.total_samples = 0
        self._noise_spectrum: Optional[np.ndarray] = None
        self._is_ready = False

    def add_noise_sample(self, audio: np.ndarray) -> None:
        """Add a noise sample (should be during confirmed silence)."""
        if self._is_ready:
            return  # Profile already built

        self.noise_samples.append(audio.copy())
        self.total_samples += len(audio)

        if self.total_samples >= self.max_samples:
            self._build_profile()

    def _build_profile(self) -> None:
        """Build the noise spectrum from collected samples."""
        if not self.noise_samples:
            return

        try:
            from scipy.signal import stft

            # Concatenate all noise samples
            noise = np.concatenate(self.noise_samples)[:self.max_samples]

            # Compute average spectrum
            _, _, Zxx = stft(noise, fs=self.sample_rate, nperseg=512, noverlap=384)
            self._noise_spectrum = np.mean(np.abs(Zxx), axis=1)
            self._is_ready = True

            print(f"Noise profile built from {len(noise)/self.sample_rate:.1f}s of audio")

        except Exception as e:
            print(f"Failed to build noise profile: {e}")

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    @property
    def noise_spectrum(self) -> Optional[np.ndarray]:
        return self._noise_spectrum

    def reset(self) -> None:
        """Reset the profiler to collect new samples."""
        self.noise_samples.clear()
        self.total_samples = 0
        self._noise_spectrum = None
        self._is_ready = False
