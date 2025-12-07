"""
Centralized constants for the transcription system.

This module consolidates all magic numbers and constants used across
multiple modules to ensure consistency and ease of maintenance.

Usage:
    from shared.constants import SPEECH_F0_MIN, SPEECH_ZCR_MAX
"""

from __future__ import annotations

import os
from typing import Final


# =============================================================================
# Audio Analysis Constants
# =============================================================================

# Fundamental frequency (pitch) range for human speech
SPEECH_F0_MIN: Final[float] = 70.0    # Hz - covers deep male voices
SPEECH_F0_MAX: Final[float] = 400.0   # Hz - covers high female voices

# Zero Crossing Rate range for human speech
SPEECH_ZCR_MIN: Final[float] = 0.02   # Below = likely DC offset or hum
SPEECH_ZCR_MAX: Final[float] = 0.30   # Above = likely white noise

# Energy analysis
ENERGY_EPSILON: Final[float] = 1e-10  # Minimum energy to avoid division by zero
MIN_AUDIO_SAMPLES_FOR_PITCH: Final[int] = 512  # Minimum samples for pitch detection


# =============================================================================
# Silero VAD Model Constants
# =============================================================================

# Model download URL (GitHub raw)
SILERO_MODEL_URL: Final[str] = (
    "https://github.com/snakers4/silero-vad/raw/master/"
    "src/silero_vad/data/silero_vad.jit"
)

# Local cache paths
SILERO_MODEL_DIR: Final[str] = os.path.join(
    os.path.dirname(__file__), "..", ".cache"
)
SILERO_MODEL_PATH: Final[str] = os.path.join(SILERO_MODEL_DIR, "silero_vad.jit")

# Silero processing parameters
SILERO_SAMPLES_16K: Final[int] = 512   # Required samples for 16kHz
SILERO_SAMPLES_8K: Final[int] = 256    # Required samples for 8kHz
SILERO_HOP_RATIO: Final[float] = 0.5   # 50% overlap for sliding window


# =============================================================================
# Calibration Constants
# =============================================================================

# Initial calibration
CALIBRATION_CHUNKS: Final[int] = 10    # ~5s at 0.5s/chunk
RECALIBRATION_SILENCE_THRESHOLD: Final[float] = 30.0  # Recalibrate after 30s silence

# Noise floor
MIN_ABSOLUTE_RMS_FLOOR: Final[float] = 0.0005  # Prevents division by zero
NOISE_FLOOR_MULTIPLIER: Final[float] = 1.1     # Dynamic threshold margin

# Adaptive detection
REFERENCE_UPDATE_ALPHA: Final[float] = 0.05    # EMA alpha (5% new, 95% old)
AMBIENT_FACTOR_MARGIN: Final[float] = 0.7      # Margin for ambient classification


# =============================================================================
# Phrase Detection Constants
# =============================================================================

# Pitch analysis
PITCH_DROP_THRESHOLD: Final[float] = 0.15  # 15% drop = falling intonation

# Silence block thresholds (with BLOCK_SECONDS = 0.5s)
# 5 blocks = 2.5s of silence before flush
SILENCE_BLOCKS_DEFINITE: Final[int] = 5    # Definite phrase end
SILENCE_BLOCKS_WITH_ENERGY: Final[int] = 5  # With energy drop
SILENCE_BLOCKS_WITH_PITCH: Final[int] = 5   # With energy + pitch drop


# =============================================================================
# Server/Timing Constants
# =============================================================================

# SSE server startup
SSE_STARTUP_TIMEOUT_SECONDS: Final[float] = 10.0  # Max wait for SSE server
SSE_STARTUP_CHECK_INTERVAL: Final[float] = 0.2    # Check interval during startup

# Broadcast timeouts
SSE_BROADCAST_TIMEOUT: Final[float] = 2.0         # Timeout for SSE broadcast lock

# Paste operation
PASTE_LOCK_TIMEOUT: Final[float] = 10.0           # Timeout for paste lock

# Diagnostics
DIAGNOSTIC_INTERVAL_SECONDS: Final[float] = 5.0   # Interval for diagnostic logging


# =============================================================================
# Logging Constants
# =============================================================================

# Log prefixes for consistent formatting
LOG_PREFIX_VAD: Final[str] = "[VAD]"
LOG_PREFIX_SSE: Final[str] = "[SSE]"
LOG_PREFIX_AUDIO: Final[str] = "[AUDIO]"
LOG_PREFIX_WHISPER: Final[str] = "[Whisper]"
LOG_PREFIX_HOTKEY: Final[str] = "[Hotkey]"
LOG_PREFIX_VISUALIZER: Final[str] = "[Visualizer]"
LOG_PREFIX_PASTE: Final[str] = "[Paste]"
LOG_PREFIX_FILTER: Final[str] = "[Filter]"
LOG_PREFIX_TOGGLE: Final[str] = "[Toggle]"
LOG_PREFIX_AUTOSLEEP: Final[str] = "[AutoSleep]"
LOG_PREFIX_ACTIVATE: Final[str] = "[Activate]"
LOG_PREFIX_DEACTIVATE: Final[str] = "[Deactivate]"
LOG_PREFIX_FORCE_FLUSH: Final[str] = "[ForceFlush]"
LOG_PREFIX_DIAG: Final[str] = "[DIAG]"
