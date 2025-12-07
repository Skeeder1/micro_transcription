"""Shared configuration - Bridge between Pydantic settings and legacy constants.

This module provides backward compatibility by exporting configuration values
as module-level constants while using Pydantic settings as the source of truth.

Usage:
    # Legacy style (still works)
    from shared import config
    sample_rate = config.SAMPLE_RATE

    # New recommended style
    from shared.settings import settings
    sample_rate = settings.audio.sample_rate
"""

from __future__ import annotations

from shared.settings import settings

# =============================================================================
# Feature Flags
# =============================================================================

ENABLE_TRANSCRIPTION: bool = settings.features.enable_transcription
ENABLE_PREVIEW: bool = settings.features.enable_preview
ENABLE_PRODUCTION: bool = settings.features.enable_production
ENABLE_ADVANCED_VAD: bool = settings.features.enable_advanced_vad
ENABLE_NOISE_REDUCTION: bool = settings.features.enable_noise_reduction
ENABLE_PHRASE_DETECTION: bool = settings.features.enable_phrase_detection
ENABLE_SPEAKER_VERIFICATION: bool = settings.features.enable_speaker_verification
ENABLE_SYSTEM_TRAY: bool = settings.features.enable_system_tray


# =============================================================================
# Audio Configuration
# =============================================================================

SAMPLE_RATE: int = settings.audio.sample_rate
BLOCK_SECONDS: float = settings.audio.block_seconds
ENERGY_THRESHOLD: float = settings.audio.energy_threshold
SILENCE_BLOCKS_BEFORE_FLUSH: int = settings.audio.silence_blocks_before_flush
MAX_PRODUCTION_SECONDS: float = settings.audio.max_production_seconds
MAX_PRODUCTION_BLOCKS: int = settings.audio.max_production_blocks


# =============================================================================
# VAD (Voice Activity Detection)
# =============================================================================

SILERO_THRESHOLD: float = settings.vad.silero_threshold
USE_ZCR_FILTER: bool = settings.vad.use_zcr_filter
ZCR_MIN: float = settings.vad.zcr_min
ZCR_MAX: float = settings.vad.zcr_max
USE_ADAPTIVE_DETECTION: bool = settings.vad.use_adaptive_detection
ADAPTIVE_BOOST_FACTOR: float = settings.vad.adaptive_boost_factor
ADAPTIVE_WINDOW_SECONDS: float = settings.vad.adaptive_window_seconds
DEBUG_VAD: bool = settings.vad.debug_vad
DEBUG_AUDIO_LEVEL: bool = settings.vad.debug_audio_level


# =============================================================================
# Whisper Model Configuration
# =============================================================================

WHISPER_MODEL: str = settings.model.whisper_model
DEVICE: str = settings.model.device
FLOAT_PRECISION: str = settings.model.float_precision
MODEL_NUM_WORKERS: int = settings.model.num_workers
LANGUAGE: str = settings.model.language
BEAM_SIZE: int = settings.model.beam_size
VAD_FILTER: bool = settings.model.vad_filter
CONDITION_ON_PREVIOUS: bool = settings.model.condition_on_previous
WORD_TIMESTAMPS: bool = settings.model.word_timestamps
BEST_OF: int = settings.model.best_of
TEMPERATURE: float = settings.model.temperature
INITIAL_PROMPT: str | None = settings.model.initial_prompt
VOCABULARY_BOOST: list[str] = settings.model.vocabulary_boost


# =============================================================================
# Preview Configuration
# =============================================================================

PREVIEW_WINDOW_SECONDS: float = settings.preview.window_seconds
PREVIEW_UPDATE_INTERVAL: float = settings.preview.update_interval
PREVIEW_TIMEOUT: float = settings.preview.timeout


# =============================================================================
# Production Configuration
# =============================================================================

RESTORE_CLIPBOARD: bool = settings.production.restore_clipboard
PASTE_DELAY_SECONDS: float = settings.production.paste_delay_seconds
APPEND_SPACE: bool = settings.production.append_space


# =============================================================================
# Noise Reduction Configuration
# =============================================================================

NOISE_REDUCTION_STRENGTH: float = settings.noise_reduction.strength
NOISE_STATIONARY: bool = settings.noise_reduction.stationary


# =============================================================================
# Phrase Detection Configuration
# =============================================================================

ENERGY_DROP_THRESHOLD: float = settings.phrase_detection.energy_drop_threshold
ENERGY_HISTORY_BLOCKS: int = settings.phrase_detection.energy_history_blocks


# =============================================================================
# Speaker Verification Configuration
# =============================================================================

SPEAKER_SIMILARITY_THRESHOLD: float = settings.speaker_verification.similarity_threshold
SPEAKER_EMBEDDING_PATH: str = settings.speaker_verification.embedding_path


# =============================================================================
# Server Configuration
# =============================================================================

SSE_HOST: str = settings.server.host
SSE_PORT: int = settings.server.port


# =============================================================================
# Visualizer Configuration
# =============================================================================

VISUALIZER_READY_DELAY: float = settings.visualizer.ready_delay
VISUALIZER_START_DELAY: float = settings.visualizer.start_delay
VISUALIZER_STOP_TIMEOUT: float = settings.visualizer.stop_timeout
VISUALIZER_KILL_TIMEOUT: float = settings.visualizer.kill_timeout


# =============================================================================
# Sleep Configuration
# =============================================================================

AUTO_SLEEP_SECONDS: float = settings.sleep.auto_sleep_seconds
DEEP_SLEEP_SECONDS: float = settings.sleep.deep_sleep_seconds
HOTKEY_TOGGLE: str = settings.sleep.hotkey_toggle
HOTKEY_SEQUENCE_WINDOW: float = settings.sleep.hotkey_sequence_window
TOGGLE_COOLDOWN_SECONDS: float = settings.sleep.toggle_cooldown_seconds
DEBUG_AUTO_SLEEP: bool = settings.sleep.debug_auto_sleep


# =============================================================================
# Miscellaneous
# =============================================================================

EXECUTOR_MAX_WORKERS: int = settings.misc.executor_max_workers


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Feature flags
    "ENABLE_TRANSCRIPTION",
    "ENABLE_PREVIEW",
    "ENABLE_PRODUCTION",
    "ENABLE_ADVANCED_VAD",
    "ENABLE_NOISE_REDUCTION",
    "ENABLE_PHRASE_DETECTION",
    "ENABLE_SPEAKER_VERIFICATION",
    "ENABLE_SYSTEM_TRAY",
    # Audio
    "SAMPLE_RATE",
    "BLOCK_SECONDS",
    "ENERGY_THRESHOLD",
    "SILENCE_BLOCKS_BEFORE_FLUSH",
    "MAX_PRODUCTION_SECONDS",
    "MAX_PRODUCTION_BLOCKS",
    # VAD
    "SILERO_THRESHOLD",
    "USE_ZCR_FILTER",
    "ZCR_MIN",
    "ZCR_MAX",
    "USE_ADAPTIVE_DETECTION",
    "ADAPTIVE_BOOST_FACTOR",
    "ADAPTIVE_WINDOW_SECONDS",
    "DEBUG_VAD",
    "DEBUG_AUDIO_LEVEL",
    # Whisper
    "WHISPER_MODEL",
    "DEVICE",
    "FLOAT_PRECISION",
    "MODEL_NUM_WORKERS",
    "LANGUAGE",
    "BEAM_SIZE",
    "VAD_FILTER",
    "CONDITION_ON_PREVIOUS",
    "WORD_TIMESTAMPS",
    "BEST_OF",
    "TEMPERATURE",
    "INITIAL_PROMPT",
    "VOCABULARY_BOOST",
    # Preview
    "PREVIEW_WINDOW_SECONDS",
    "PREVIEW_UPDATE_INTERVAL",
    "PREVIEW_TIMEOUT",
    # Production
    "RESTORE_CLIPBOARD",
    "PASTE_DELAY_SECONDS",
    "APPEND_SPACE",
    # Noise reduction
    "NOISE_REDUCTION_STRENGTH",
    "NOISE_STATIONARY",
    # Phrase detection
    "ENERGY_DROP_THRESHOLD",
    "ENERGY_HISTORY_BLOCKS",
    # Speaker verification
    "SPEAKER_SIMILARITY_THRESHOLD",
    "SPEAKER_EMBEDDING_PATH",
    # Server
    "SSE_HOST",
    "SSE_PORT",
    # Visualizer
    "VISUALIZER_READY_DELAY",
    "VISUALIZER_START_DELAY",
    "VISUALIZER_STOP_TIMEOUT",
    "VISUALIZER_KILL_TIMEOUT",
    # Sleep
    "AUTO_SLEEP_SECONDS",
    "DEEP_SLEEP_SECONDS",
    "HOTKEY_TOGGLE",
    "HOTKEY_SEQUENCE_WINDOW",
    "TOGGLE_COOLDOWN_SECONDS",
    "DEBUG_AUTO_SLEEP",
    # Misc
    "EXECUTOR_MAX_WORKERS",
    # Settings object for direct access
    "settings",
]
