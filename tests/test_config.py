"""Tests for configuration module."""

import pytest


class TestCoreConfig:
    """Tests for core configuration."""

    def test_audio_config(self):
        """Test audio configuration values."""
        from shared import config

        assert config.SAMPLE_RATE == 16000
        assert config.BLOCK_SECONDS == 0.5
        assert config.ENERGY_THRESHOLD > 0

    def test_model_config(self):
        """Test model configuration values."""
        from shared import config

        assert config.WHISPER_MODEL in ["tiny", "base", "small", "medium", "large"]
        assert config.DEVICE in ["cuda", "cpu"]
        assert config.LANGUAGE == "fr"

    def test_transcription_params(self):
        """Test transcription parameters."""
        from shared import config

        assert 1 <= config.BEAM_SIZE <= 10
        assert 0.0 <= config.TEMPERATURE <= 1.0
        assert config.BEST_OF >= 1


class TestVADConfig:
    """Tests for VAD configuration."""

    def test_vad_enabled(self):
        """Test advanced VAD is enabled."""
        from shared import config

        assert config.ENABLE_ADVANCED_VAD is True

    def test_silero_threshold(self):
        """Test Silero threshold is valid."""
        from shared import config

        assert 0.0 <= config.SILERO_THRESHOLD <= 1.0

    def test_zcr_config(self):
        """Test ZCR configuration."""
        from shared import config

        assert config.USE_ZCR_FILTER in [True, False]
        assert config.ZCR_MIN < config.ZCR_MAX
        assert 0.0 <= config.ZCR_MIN <= 1.0
        assert 0.0 <= config.ZCR_MAX <= 1.0

    def test_adaptive_detection(self):
        """Test adaptive detection configuration."""
        from shared import config

        assert config.USE_ADAPTIVE_DETECTION in [True, False]
        assert config.ADAPTIVE_BOOST_FACTOR >= 1.0
        assert config.ADAPTIVE_WINDOW_SECONDS > 0


class TestNoiseReductionConfig:
    """Tests for noise reduction configuration."""

    def test_noise_reduction_enabled(self):
        """Test noise reduction is enabled."""
        from shared import config

        assert config.ENABLE_NOISE_REDUCTION is True

    def test_noise_reduction_strength(self):
        """Test noise reduction strength is valid."""
        from shared import config

        assert 0.0 <= config.NOISE_REDUCTION_STRENGTH <= 1.0

    def test_noise_stationary(self):
        """Test noise stationary setting."""
        from shared import config

        assert config.NOISE_STATIONARY in [True, False]


class TestPhraseDetectionConfig:
    """Tests for phrase detection configuration."""

    def test_phrase_detection_enabled(self):
        """Test phrase detection is enabled."""
        from shared import config

        assert config.ENABLE_PHRASE_DETECTION is True

    def test_energy_drop_threshold(self):
        """Test energy drop threshold is valid."""
        from shared import config

        assert 0.0 <= config.ENERGY_DROP_THRESHOLD <= 1.0

    def test_energy_history_blocks(self):
        """Test energy history blocks is positive."""
        from shared import config

        assert config.ENERGY_HISTORY_BLOCKS > 0


class TestBufferConfig:
    """Tests for buffer configuration."""

    def test_max_production_seconds(self):
        """Test max production seconds is set."""
        from shared import config

        assert config.MAX_PRODUCTION_SECONDS > 0
        assert config.MAX_PRODUCTION_SECONDS == 30.0

    def test_max_production_blocks(self):
        """Test max production blocks is calculated correctly."""
        from shared import config

        expected = int(config.MAX_PRODUCTION_SECONDS / config.BLOCK_SECONDS)
        assert config.MAX_PRODUCTION_BLOCKS == expected


class TestWhisperPromptConfig:
    """Tests for Whisper prompt configuration."""

    def test_initial_prompt_set(self):
        """Test initial prompt is set."""
        from shared import config

        assert config.INITIAL_PROMPT is not None
        assert len(config.INITIAL_PROMPT) > 0

    def test_vocabulary_boost_list(self):
        """Test vocabulary boost is a list."""
        from shared import config

        assert isinstance(config.VOCABULARY_BOOST, list)
        assert len(config.VOCABULARY_BOOST) > 0


class TestSpeakerVerificationConfig:
    """Tests for speaker verification configuration."""

    def test_speaker_verification_default_off(self):
        """Test speaker verification is off by default."""
        from shared import config

        # Default should be False (needs enrollment)
        assert config.ENABLE_SPEAKER_VERIFICATION is False

    def test_speaker_similarity_threshold(self):
        """Test speaker similarity threshold is valid."""
        from shared import config

        assert 0.0 <= config.SPEAKER_SIMILARITY_THRESHOLD <= 1.0

    def test_speaker_embedding_path(self):
        """Test speaker embedding path is set."""
        from shared import config

        assert config.SPEAKER_EMBEDDING_PATH is not None
        assert len(config.SPEAKER_EMBEDDING_PATH) > 0


class TestSleepConfig:
    """Tests for sleep configuration."""

    def test_auto_sleep_seconds(self):
        """Test auto sleep seconds is set."""
        from shared import config

        assert config.AUTO_SLEEP_SECONDS > 0

    def test_deep_sleep_seconds(self):
        """Test deep sleep seconds is set."""
        from shared import config

        assert config.DEEP_SLEEP_SECONDS > 0
        assert config.DEEP_SLEEP_SECONDS > config.AUTO_SLEEP_SECONDS

    def test_hotkey_toggle(self):
        """Test hotkey toggle is set."""
        from shared import config

        assert config.HOTKEY_TOGGLE is not None
        assert len(config.HOTKEY_TOGGLE) > 0
