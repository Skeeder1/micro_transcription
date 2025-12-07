"""Unit tests for Pydantic settings configuration."""

import pytest
from pydantic import ValidationError

from shared.settings import (
    Settings,
    FeatureFlags,
    AudioConfig,
    VADConfig,
    ModelConfig,
    PreviewConfig,
    ProductionConfig,
    NoiseReductionConfig,
    PhraseDetectionConfig,
    SpeakerVerificationConfig,
    ServerConfig,
    VisualizerConfig,
    SleepConfig,
    MiscConfig,
    get_settings,
)


class TestFeatureFlags:
    """Test the FeatureFlags configuration."""

    def test_default_values(self):
        """Test default feature flag values."""
        flags = FeatureFlags()

        assert flags.enable_transcription is True
        assert flags.enable_preview is False
        assert flags.enable_production is True
        assert flags.enable_advanced_vad is True

    def test_custom_values(self):
        """Test setting custom values."""
        flags = FeatureFlags(
            enable_transcription=False,
            enable_preview=True,
        )

        assert flags.enable_transcription is False
        assert flags.enable_preview is True


class TestAudioConfig:
    """Test the AudioConfig configuration."""

    def test_default_values(self):
        """Test default audio config values."""
        config = AudioConfig()

        assert config.sample_rate == 16000
        assert config.block_seconds == 0.5
        assert config.energy_threshold == 0.004

    def test_validation_sample_rate(self):
        """Test sample rate validation."""
        # Valid range
        config = AudioConfig(sample_rate=8000)
        assert config.sample_rate == 8000

        config = AudioConfig(sample_rate=48000)
        assert config.sample_rate == 48000

        # Invalid range
        with pytest.raises(ValidationError):
            AudioConfig(sample_rate=7999)

        with pytest.raises(ValidationError):
            AudioConfig(sample_rate=48001)

    def test_validation_block_seconds(self):
        """Test block_seconds validation."""
        config = AudioConfig(block_seconds=0.1)
        assert config.block_seconds == 0.1

        with pytest.raises(ValidationError):
            AudioConfig(block_seconds=0.05)

        with pytest.raises(ValidationError):
            AudioConfig(block_seconds=2.5)

    def test_max_production_blocks_computed(self):
        """Test max_production_blocks is computed."""
        config = AudioConfig(
            block_seconds=0.5,
            max_production_seconds=30.0,
        )

        assert config.max_production_blocks == 60  # 30.0 / 0.5


class TestVADConfig:
    """Test the VADConfig configuration."""

    def test_default_values(self):
        """Test default VAD config values."""
        config = VADConfig()

        assert config.silero_threshold == 0.1
        assert config.use_zcr_filter is True
        assert 0.0 <= config.zcr_min <= 1.0
        assert 0.0 <= config.zcr_max <= 1.0

    def test_threshold_validation(self):
        """Test threshold validation."""
        config = VADConfig(silero_threshold=0.5)
        assert config.silero_threshold == 0.5

        with pytest.raises(ValidationError):
            VADConfig(silero_threshold=-0.1)

        with pytest.raises(ValidationError):
            VADConfig(silero_threshold=1.1)


class TestModelConfig:
    """Test the ModelConfig configuration."""

    def test_default_values(self):
        """Test default model config values."""
        config = ModelConfig()

        assert config.whisper_model == "large"
        assert config.device in ["cuda", "cpu"]
        assert config.language == "fr"

    def test_valid_model_names(self):
        """Test valid model names."""
        for model in ["tiny", "base", "small", "medium", "large"]:
            config = ModelConfig(whisper_model=model)
            assert config.whisper_model == model

    def test_invalid_model_name(self):
        """Test invalid model name."""
        with pytest.raises(ValidationError):
            ModelConfig(whisper_model="invalid_model")

    def test_valid_devices(self):
        """Test valid device values."""
        for device in ["cuda", "cpu"]:
            config = ModelConfig(device=device)
            assert config.device == device

    def test_beam_size_validation(self):
        """Test beam_size validation."""
        config = ModelConfig(beam_size=1)
        assert config.beam_size == 1

        config = ModelConfig(beam_size=10)
        assert config.beam_size == 10

        with pytest.raises(ValidationError):
            ModelConfig(beam_size=0)

        with pytest.raises(ValidationError):
            ModelConfig(beam_size=11)


class TestPreviewConfig:
    """Test the PreviewConfig configuration."""

    def test_default_values(self):
        """Test default preview config values."""
        config = PreviewConfig()

        assert config.window_seconds > 0
        assert config.update_interval > 0
        assert config.timeout > 0


class TestProductionConfig:
    """Test the ProductionConfig configuration."""

    def test_default_values(self):
        """Test default production config values."""
        config = ProductionConfig()

        assert config.restore_clipboard is True
        assert config.paste_delay_seconds >= 0
        assert isinstance(config.append_space, bool)


class TestNoiseReductionConfig:
    """Test the NoiseReductionConfig configuration."""

    def test_default_values(self):
        """Test default noise reduction config values."""
        config = NoiseReductionConfig()

        assert 0 <= config.strength <= 1
        assert isinstance(config.stationary, bool)

    def test_strength_validation(self):
        """Test strength validation."""
        config = NoiseReductionConfig(strength=0.0)
        assert config.strength == 0.0

        config = NoiseReductionConfig(strength=1.0)
        assert config.strength == 1.0

        with pytest.raises(ValidationError):
            NoiseReductionConfig(strength=-0.1)

        with pytest.raises(ValidationError):
            NoiseReductionConfig(strength=1.1)


class TestServerConfig:
    """Test the ServerConfig configuration."""

    def test_default_values(self):
        """Test default server config values."""
        config = ServerConfig()

        assert config.host == "127.0.0.1"
        assert config.port == 5433

    def test_port_validation(self):
        """Test port validation."""
        config = ServerConfig(port=1024)
        assert config.port == 1024

        config = ServerConfig(port=65535)
        assert config.port == 65535

        with pytest.raises(ValidationError):
            ServerConfig(port=1023)

        with pytest.raises(ValidationError):
            ServerConfig(port=65536)


class TestVisualizerConfig:
    """Test the VisualizerConfig configuration."""

    def test_default_values(self):
        """Test default visualizer config values."""
        config = VisualizerConfig()

        assert config.ready_delay > 0
        assert config.start_delay > 0
        assert config.stop_timeout > 0
        assert config.kill_timeout > 0


class TestSleepConfig:
    """Test the SleepConfig configuration."""

    def test_default_values(self):
        """Test default sleep config values."""
        config = SleepConfig()

        assert config.auto_sleep_seconds > 0
        assert config.deep_sleep_seconds > 0
        assert config.hotkey_toggle == "F9"
        assert config.toggle_cooldown_seconds > 0


class TestSettings:
    """Test the main Settings class."""

    def test_settings_creation(self):
        """Test creating settings object."""
        settings = Settings()

        assert settings.features is not None
        assert settings.audio is not None
        assert settings.vad is not None
        assert settings.model is not None
        assert settings.preview is not None
        assert settings.production is not None

    def test_nested_config_access(self):
        """Test accessing nested configuration."""
        settings = Settings()

        assert settings.audio.sample_rate == 16000
        assert settings.vad.silero_threshold == 0.1
        assert settings.model.language == "fr"

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same instance (cached)
        assert settings1 is settings2

    def test_legacy_config_access(self):
        """Test accessing settings via legacy config bridge."""
        from shared import config

        settings = get_settings()

        assert config.SAMPLE_RATE == settings.audio.sample_rate
        assert config.SILERO_THRESHOLD == settings.vad.silero_threshold
        assert config.WHISPER_MODEL == settings.model.whisper_model


class TestEnvironmentOverrides:
    """Test environment variable overrides."""

    def test_env_prefix(self):
        """Test that settings use TRANSCRIBE_ prefix."""
        settings = Settings()

        # Check model_config for env_prefix
        assert settings.model_config.get("env_prefix") == "TRANSCRIBE_"
