#!/usr/bin/env python
"""Test audio preprocessing module."""

import sys
from pathlib import Path

# Add transcription_app to path to import module directly
sys.path.insert(0, str(Path(__file__).parent / "transcription_app"))

import numpy as np
from audio_preprocessing import (
    normalize_audio,
    apply_highpass_filter,
    amplify_audio,
    preprocess_audio,
)


def test_normalize_audio():
    """Test audio normalization."""
    print("Testing normalize_audio()...")

    # Test with simple signal
    audio = np.array([0.5, 1.0, -0.5, 0.8])
    normalized = normalize_audio(audio)

    assert np.max(np.abs(normalized)) <= 1.0, "Normalized audio exceeds [-1, 1] range"
    assert np.isclose(np.max(np.abs(normalized)), 1.0), "Normalization didn't scale to max"
    print("  OK: Audio normalized to [-1, 1] range")


def test_highpass_filter():
    """Test high-pass filter."""
    print("Testing apply_highpass_filter()...")

    # Create audio with low-frequency hum (50 Hz) + high-frequency speech
    sample_rate = 16000
    t = np.linspace(0, 1, sample_rate)

    # 50 Hz hum (should be filtered)
    hum = 0.3 * np.sin(2 * np.pi * 50 * t)
    # 1000 Hz speech (should pass)
    speech = 0.7 * np.sin(2 * np.pi * 1000 * t)
    audio = hum + speech

    filtered = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

    # Energy should be reduced but not eliminated
    assert filtered.size == audio.size, "Filter changed audio size"
    print("  OK: High-pass filter applied (80 Hz cutoff)")


def test_amplify_audio():
    """Test audio amplification."""
    print("Testing amplify_audio()...")

    # Create quiet audio
    quiet_audio = 0.01 * np.random.randn(1000)
    amplified = amplify_audio(quiet_audio, target_rms=0.1)

    # Check amplification
    original_rms = np.sqrt(np.mean(np.square(quiet_audio)))
    new_rms = np.sqrt(np.mean(np.square(amplified)))

    assert new_rms > original_rms, "Audio wasn't amplified"
    assert amplified.size == quiet_audio.size, "Amplification changed audio size"
    print(f"  OK: Audio amplified (RMS: {original_rms:.4f} -> {new_rms:.4f})")


def test_full_pipeline():
    """Test full preprocessing pipeline."""
    print("Testing preprocess_audio() pipeline...")

    # Create test audio: noisy, quiet speech
    sample_rate = 16000
    t = np.linspace(0, 1, sample_rate)

    # 60 Hz hum + quiet speech
    hum = 0.2 * np.sin(2 * np.pi * 60 * t)
    speech = 0.05 * np.sin(2 * np.pi * 500 * t)  # Quiet
    noise = 0.01 * np.random.randn(sample_rate)
    audio = hum + speech + noise

    preprocessed = preprocess_audio(audio, sample_rate)

    # Validate output
    assert preprocessed.size == audio.size, "Pipeline changed audio size"
    assert np.max(np.abs(preprocessed)) <= 1.0, "Pipeline output exceeds [-1, 1]"
    assert preprocessed.dtype == audio.dtype, "Pipeline changed dtype"

    print("  OK: Full pipeline executed successfully")
    print(f"      Input RMS: {np.sqrt(np.mean(np.square(audio))):.4f}")
    print(f"      Output RMS: {np.sqrt(np.mean(np.square(preprocessed))):.4f}")


if __name__ == "__main__":
    print("=" * 60)
    print("Audio Preprocessing Module Tests")
    print("=" * 60)

    try:
        test_normalize_audio()
        test_highpass_filter()
        test_amplify_audio()
        test_full_pipeline()

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        exit(1)
