"""Pytest configuration and shared fixtures."""

import sys
import os
from pathlib import Path

import numpy as np
import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def sample_rate():
    """Standard sample rate for tests."""
    return 16000


@pytest.fixture
def block_samples(sample_rate):
    """Number of samples per audio block (0.5s)."""
    return int(sample_rate * 0.5)


@pytest.fixture
def silence_audio(block_samples):
    """Generate silent audio block."""
    return np.zeros(block_samples, dtype=np.float32)


@pytest.fixture
def noise_audio(block_samples):
    """Generate white noise audio block."""
    np.random.seed(42)
    return (np.random.randn(block_samples) * 0.01).astype(np.float32)


@pytest.fixture
def loud_noise_audio(block_samples):
    """Generate loud noise audio block."""
    np.random.seed(42)
    return (np.random.randn(block_samples) * 0.3).astype(np.float32)


@pytest.fixture
def speech_like_audio(sample_rate):
    """Generate audio that mimics speech characteristics."""
    duration = 0.5
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Fundamental frequency around 150Hz (male voice)
    f0 = 150
    audio = np.sin(2 * np.pi * f0 * t)

    # Add harmonics
    audio += 0.5 * np.sin(2 * np.pi * 2 * f0 * t)
    audio += 0.3 * np.sin(2 * np.pi * 3 * f0 * t)
    audio += 0.2 * np.sin(2 * np.pi * 4 * f0 * t)

    # Add some noise
    audio += np.random.randn(len(audio)) * 0.05

    # Normalize
    audio = audio / np.abs(audio).max() * 0.5

    return audio.astype(np.float32)


@pytest.fixture
def app_context():
    """Create application context for testing."""
    from shared.context import AppContext
    return AppContext()


@pytest.fixture
def voice_detector(sample_rate):
    """Create voice detector instance."""
    from core.voice_detector import VoiceDetector
    return VoiceDetector(
        sample_rate=sample_rate,
        silero_threshold=0.5,
        use_zcr_filter=True,
        use_adaptive=True,
        adaptive_boost_factor=2.5,
    )


@pytest.fixture
def phrase_detector(sample_rate):
    """Create phrase detector instance."""
    from core.phrase_detector import PhraseEndDetector
    return PhraseEndDetector(
        sample_rate=sample_rate,
        history_size=5,
        energy_drop_threshold=0.3,
    )


@pytest.fixture
def speaker_verifier(sample_rate):
    """Create speaker verifier instance with clean state."""
    from core.speaker_detector import SpeakerVerifier
    sv = SpeakerVerifier(
        sample_rate=sample_rate,
        embedding_dim=64,
        similarity_threshold=0.7,
    )
    # Reset any loaded embedding to ensure clean test state
    sv._user_embedding = None
    sv._is_enrolled = False
    sv._enrollment_samples.clear()
    return sv
