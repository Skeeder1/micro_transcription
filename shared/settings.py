"""
Pydantic-based configuration system.

This module provides a validated, typed configuration system using Pydantic.
It supports loading from environment variables and .env files.

Usage:
    from shared.settings import settings

    # Access configuration
    sample_rate = settings.audio.sample_rate
    whisper_model = settings.model.whisper_model

    # All values are validated and typed
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# Feature Flags
# =============================================================================

class FeatureFlags(BaseModel):
    """Feature flags for enabling/disabling functionality."""

    enable_transcription: bool = Field(
        default=True,
        description="Enable Whisper transcription (False = visualizer only)"
    )
    enable_preview: bool = Field(
        default=False,
        description="Enable real-time preview in visualizer"
    )
    enable_production: bool = Field(
        default=True,
        description="Enable final transcription pasted to cursor"
    )
    enable_advanced_vad: bool = Field(
        default=True,
        description="Enable Silero VAD + ZCR filtering"
    )
    enable_noise_reduction: bool = Field(
        default=False,
        description="Enable noise reduction (experimental)"
    )
    enable_phrase_detection: bool = Field(
        default=True,
        description="Enable intelligent phrase end detection"
    )
    enable_speaker_verification: bool = Field(
        default=False,
        description="Enable speaker verification (requires enrollment)"
    )
    enable_system_tray: bool = Field(
        default=False,
        description="Enable system tray icon"
    )


# =============================================================================
# Audio Configuration
# =============================================================================

class AudioConfig(BaseModel):
    """Audio capture and processing configuration."""

    sample_rate: int = Field(
        default=16000,
        ge=8000,
        le=48000,
        description="Audio sample rate in Hz"
    )
    block_seconds: float = Field(
        default=0.5,
        ge=0.1,
        le=2.0,
        description="Duration of each audio block in seconds"
    )
    energy_threshold: float = Field(
        default=0.004,
        ge=0.0001,
        le=0.1,
        description="RMS energy threshold for voice detection"
    )
    silence_blocks_before_flush: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of silent blocks before finalizing transcription"
    )
    max_production_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Maximum recording duration before forced flush"
    )

    @property
    def max_production_blocks(self) -> int:
        """Calculate max blocks from seconds and block duration."""
        return int(self.max_production_seconds / self.block_seconds)


# =============================================================================
# VAD (Voice Activity Detection) Configuration
# =============================================================================

class VADConfig(BaseModel):
    """Voice activity detection configuration."""

    silero_threshold: float = Field(
        default=0.1,
        ge=0.01,
        le=1.0,
        description="Silero VAD probability threshold"
    )
    use_zcr_filter: bool = Field(
        default=True,
        description="Enable Zero Crossing Rate filtering"
    )
    zcr_min: float = Field(
        default=0.02,
        ge=0.0,
        le=0.5,
        description="Minimum ZCR for voice"
    )
    zcr_max: float = Field(
        default=0.30,
        ge=0.1,
        le=1.0,
        description="Maximum ZCR for voice"
    )
    use_adaptive_detection: bool = Field(
        default=True,
        description="Enable adaptive ambient noise detection"
    )
    adaptive_boost_factor: float = Field(
        default=1.2,
        ge=1.0,
        le=5.0,
        description="Voice must be X times louder than ambient"
    )
    adaptive_window_seconds: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Duration of reference window for ambient level"
    )
    debug_vad: bool = Field(
        default=True,
        description="Enable VAD debug output"
    )
    debug_audio_level: bool = Field(
        default=True,
        description="Enable audio level debug output"
    )


# =============================================================================
# Whisper Model Configuration
# =============================================================================

class ModelConfig(BaseModel):
    """Whisper model configuration."""

    whisper_model: Literal["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"] = Field(
        default="large",
        description="Whisper model size"
    )
    device: Literal["cuda", "cpu", "auto"] = Field(
        default="cuda",
        description="Compute device"
    )
    float_precision: Literal["float16", "float32", "int8"] = Field(
        default="float16",
        description="Model precision"
    )
    num_workers: int = Field(
        default=2,
        ge=1,
        le=8,
        description="Number of model loading workers"
    )
    language: str = Field(
        default="fr",
        min_length=2,
        max_length=5,
        description="Transcription language code"
    )
    beam_size: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Beam search size"
    )
    vad_filter: bool = Field(
        default=False,
        description="Enable Whisper's internal VAD filter"
    )
    condition_on_previous: bool = Field(
        default=True,
        description="Condition on previous transcription text"
    )
    word_timestamps: bool = Field(
        default=False,
        description="Generate word-level timestamps"
    )
    best_of: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Number of candidates to evaluate"
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Sampling temperature"
    )
    initial_prompt: Optional[str] = Field(
        default="Transcription de dictée vocale en français.\nLe locuteur parle clairement avec une prononciation standard.",
        description="Initial context prompt for Whisper"
    )
    vocabulary_boost: List[str] = Field(
        default_factory=lambda: [
            "Claude", "Anthropic", "Python", "JavaScript", "TypeScript",
            "Linux", "Ubuntu", "Windows", "Docker", "Git", "GitHub",
        ],
        description="Custom vocabulary to boost recognition"
    )


# =============================================================================
# Preview Configuration
# =============================================================================

class PreviewConfig(BaseModel):
    """Real-time preview configuration."""

    window_seconds: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Sliding window duration for preview"
    )
    update_interval: float = Field(
        default=1.0,
        ge=0.5,
        le=5.0,
        description="Minimum interval between preview updates"
    )
    timeout: float = Field(
        default=20.0,
        ge=5.0,
        le=60.0,
        description="Maximum time for preview transcription"
    )


# =============================================================================
# Production Configuration
# =============================================================================

class ProductionConfig(BaseModel):
    """Final transcription and paste configuration."""

    restore_clipboard: bool = Field(
        default=True,
        description="Restore original clipboard after paste"
    )
    paste_delay_seconds: float = Field(
        default=0.05,
        ge=0.0,
        le=1.0,
        description="Delay before pasting"
    )
    append_space: bool = Field(
        default=True,
        description="Add space after pasted text"
    )


# =============================================================================
# Noise Reduction Configuration
# =============================================================================

class NoiseReductionConfig(BaseModel):
    """Noise reduction configuration."""

    strength: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Noise reduction strength"
    )
    stationary: bool = Field(
        default=False,
        description="Use stationary noise mode"
    )


# =============================================================================
# Phrase Detection Configuration
# =============================================================================

class PhraseDetectionConfig(BaseModel):
    """Phrase end detection configuration."""

    energy_drop_threshold: float = Field(
        default=0.3,
        ge=0.1,
        le=0.9,
        description="Energy drop threshold for phrase end"
    )
    energy_history_blocks: int = Field(
        default=5,
        ge=2,
        le=20,
        description="Number of blocks for energy trend calculation"
    )


# =============================================================================
# Speaker Verification Configuration
# =============================================================================

class SpeakerVerificationConfig(BaseModel):
    """Speaker verification configuration."""

    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for speaker match"
    )
    embedding_path: str = Field(
        default="data/user_embedding.npy",
        description="Path to speaker embedding file"
    )


# =============================================================================
# Server Configuration
# =============================================================================

class ServerConfig(BaseModel):
    """SSE server configuration."""

    host: str = Field(
        default="127.0.0.1",
        description="Server host address"
    )
    port: int = Field(
        default=5433,
        ge=1024,
        le=65535,
        description="Server port"
    )


# =============================================================================
# Visualizer Configuration
# =============================================================================

class VisualizerConfig(BaseModel):
    """Visualizer window configuration."""

    ready_delay: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Delay for visualizer to be ready"
    )
    start_delay: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Delay after visualizer start"
    )
    stop_timeout: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Timeout for graceful stop"
    )
    kill_timeout: float = Field(
        default=1.0,
        ge=0.5,
        le=5.0,
        description="Timeout for force kill"
    )


# =============================================================================
# Sleep Configuration
# =============================================================================

class SleepConfig(BaseModel):
    """Sleep and hotkey configuration."""

    auto_sleep_seconds: float = Field(
        default=30.0,
        ge=5.0,
        le=300.0,
        description="Inactivity duration before auto-sleep"
    )
    deep_sleep_seconds: float = Field(
        default=1800.0,
        ge=60.0,
        le=7200.0,
        description="Sleep duration before deep sleep (unload models)"
    )
    hotkey_toggle: str = Field(
        default="F9",
        description="Hotkey for sleep toggle"
    )
    hotkey_sequence_window: float = Field(
        default=0.6,
        ge=0.1,
        le=2.0,
        description="Time window for hotkey sequences"
    )
    toggle_cooldown_seconds: float = Field(
        default=1.0,
        ge=0.5,
        le=5.0,
        description="Minimum time between toggles"
    )
    debug_auto_sleep: bool = Field(
        default=False,
        description="Enable auto-sleep debug output"
    )


# =============================================================================
# Miscellaneous Configuration
# =============================================================================

class MiscConfig(BaseModel):
    """Miscellaneous configuration."""

    executor_max_workers: int = Field(
        default=2,
        ge=1,
        le=8,
        description="Maximum parallel workers"
    )


# =============================================================================
# Root Settings
# =============================================================================

class Settings(BaseSettings):
    """
    Root configuration object.

    All configuration is organized into logical groups.
    Values can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="TRANSCRIBE_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Configuration groups
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    vad: VADConfig = Field(default_factory=VADConfig)
    model: ModelConfig = Field(default_factory=ModelConfig)
    preview: PreviewConfig = Field(default_factory=PreviewConfig)
    production: ProductionConfig = Field(default_factory=ProductionConfig)
    noise_reduction: NoiseReductionConfig = Field(default_factory=NoiseReductionConfig)
    phrase_detection: PhraseDetectionConfig = Field(default_factory=PhraseDetectionConfig)
    speaker_verification: SpeakerVerificationConfig = Field(default_factory=SpeakerVerificationConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    visualizer: VisualizerConfig = Field(default_factory=VisualizerConfig)
    sleep: SleepConfig = Field(default_factory=SleepConfig)
    misc: MiscConfig = Field(default_factory=MiscConfig)


@lru_cache()
def get_settings() -> Settings:
    """
    Get the cached settings instance.

    Uses lru_cache for singleton-like behavior.
    Call get_settings.cache_clear() to reload settings.
    """
    return Settings()


# Singleton instance for convenience
settings = get_settings()
