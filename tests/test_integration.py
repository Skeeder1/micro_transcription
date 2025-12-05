"""Integration tests for the complete transcription system."""

import time
import queue
import threading
import numpy as np
import pytest


class TestAppContext:
    """Tests for application context."""

    def test_context_creation(self, app_context):
        """Test application context creates successfully."""
        assert app_context is not None
        assert app_context.audio_queue is not None
        assert app_context.is_sleeping is False

    def test_context_has_required_attributes(self, app_context):
        """Test context has all required attributes."""
        required_attrs = [
            'audio_queue',
            'is_sleeping',
            'is_deep_sleeping',
            'sleep_lock',
            'model_lock',
            'executor',
        ]

        for attr in required_attrs:
            assert hasattr(app_context, attr), f"Missing attribute: {attr}"

    def test_context_queue_operations(self, app_context, noise_audio):
        """Test audio queue operations."""
        # Put audio in queue
        app_context.audio_queue.put(noise_audio)

        # Get audio from queue
        retrieved = app_context.audio_queue.get(timeout=1.0)

        assert np.array_equal(retrieved, noise_audio)


class TestSleepMechanism:
    """Tests for sleep/wake functionality."""

    def test_sleep_state_toggle(self, app_context):
        """Test sleep state can be toggled."""
        from shared.sleep import enter_sleep_mode, exit_sleep_mode, is_sleeping

        assert is_sleeping(app_context) is False

        enter_sleep_mode(app_context, manual=True)
        assert is_sleeping(app_context) is True

        exit_sleep_mode(app_context)
        assert is_sleeping(app_context) is False

    def test_manual_sleep_flag(self, app_context):
        """Test manual sleep flag is set correctly."""
        from shared.sleep import enter_sleep_mode

        enter_sleep_mode(app_context, manual=True)

        assert app_context.manual_sleep is True

    def test_auto_sleep_timer(self, app_context):
        """Test auto-sleep timer functionality."""
        from shared.sleep import update_speech_timer

        # Update speech timer
        update_speech_timer(app_context)

        # Last speech time should be recent
        assert app_context.last_speech_time > 0

    def test_deep_sleep_state(self, app_context):
        """Test deep sleep state."""
        from shared.sleep import enter_sleep_mode

        enter_sleep_mode(app_context, manual=True)

        # Initially not in deep sleep
        assert app_context.is_deep_sleeping is False


class TestConfigurationIntegration:
    """Tests for configuration integration."""

    def test_all_new_configs_accessible(self):
        """Test all new configurations are accessible."""
        from shared import config

        new_configs = [
            'ENABLE_ADVANCED_VAD',
            'ENABLE_NOISE_REDUCTION',
            'ENABLE_PHRASE_DETECTION',
            'MAX_PRODUCTION_SECONDS',
            'MAX_PRODUCTION_BLOCKS',
            'INITIAL_PROMPT',
            'VOCABULARY_BOOST',
            'NOISE_REDUCTION_STRENGTH',
            'ENERGY_DROP_THRESHOLD',
            'ENABLE_SPEAKER_VERIFICATION',
        ]

        for cfg in new_configs:
            assert hasattr(config, cfg), f"Missing config: {cfg}"

    def test_config_values_reasonable(self):
        """Test configuration values are reasonable."""
        from shared import config

        assert 0.0 <= config.SILERO_THRESHOLD <= 1.0
        assert 0.0 <= config.NOISE_REDUCTION_STRENGTH <= 1.0
        assert config.MAX_PRODUCTION_SECONDS > 0
        assert config.MAX_PRODUCTION_BLOCKS > 0
        assert config.ADAPTIVE_BOOST_FACTOR >= 1.0


class TestAudioPipelineIntegration:
    """Tests for audio processing pipeline integration."""

    def test_full_pipeline_flow(self, sample_rate, noise_audio):
        """Test complete audio processing flow."""
        from core.voice_detector import VoiceDetector
        from core.phrase_detector import PhraseEndDetector
        from core.audio_preprocessing import preprocess_audio
        from core.audio_capture import detect_activity

        # Create components
        vd = VoiceDetector(sample_rate=sample_rate)
        pd = PhraseEndDetector(sample_rate=sample_rate)

        # Process audio through pipeline
        is_voice = detect_activity(noise_audio, vd)
        pd.update(noise_audio, not is_voice)
        processed = preprocess_audio(noise_audio, sample_rate, for_production=True)

        assert processed is not None
        assert len(processed) == len(noise_audio)

    def test_buffer_limit_calculation(self):
        """Test buffer limit is calculated correctly."""
        from shared import config

        expected_blocks = int(config.MAX_PRODUCTION_SECONDS / config.BLOCK_SECONDS)
        assert config.MAX_PRODUCTION_BLOCKS == expected_blocks

    def test_preprocessing_modes(self, sample_rate, noise_audio):
        """Test different preprocessing modes."""
        from core.audio_preprocessing import preprocess_audio

        # Production mode (with noise reduction)
        prod = preprocess_audio(noise_audio, sample_rate, for_production=True)
        assert prod is not None

        # Preview mode (without noise reduction)
        prev = preprocess_audio(noise_audio, sample_rate, for_production=False)
        assert prev is not None


class TestModelIntegration:
    """Tests for Whisper model integration."""

    def test_model_config_with_prompt(self):
        """Test model configuration includes initial prompt."""
        from shared import config

        assert config.INITIAL_PROMPT is not None
        assert len(config.INITIAL_PROMPT) > 0

    def test_vocabulary_boost_configured(self):
        """Test vocabulary boost is configured."""
        from shared import config

        assert isinstance(config.VOCABULARY_BOOST, list)


class TestDetectorIntegration:
    """Tests for detector integration."""

    def test_voice_detector_with_phrase_detector(
        self, voice_detector, phrase_detector, noise_audio, loud_noise_audio
    ):
        """Test voice detector works with phrase detector."""
        # Calibrate voice detector
        for _ in range(5):
            is_voice = voice_detector.is_human_speech(noise_audio)
            phrase_detector.update(noise_audio, not is_voice)

        # Process loud audio
        is_voice = voice_detector.is_human_speech(loud_noise_audio)
        phrase_detector.update(loud_noise_audio, not is_voice)

        # Get metrics from both
        vd_metrics = voice_detector.get_metrics()
        pd_metrics = phrase_detector.get_metrics()

        assert "rms" in vd_metrics
        assert "current_energy" in pd_metrics

    def test_complete_detection_flow(self, sample_rate):
        """Test complete detection flow from speech to silence."""
        from core.phrase_detector import PhraseEndDetector

        # Create fresh phrase detector
        pd = PhraseEndDetector(sample_rate=sample_rate)

        # Simulate speech (loud audio)
        speech = np.random.randn(8000).astype(np.float32) * 0.3
        for _ in range(3):
            pd.update(speech, is_silent=False)

        # Simulate silence (very quiet audio)
        silence = np.zeros(8000, dtype=np.float32)
        for _ in range(4):  # Need enough silence blocks
            pd.update(silence, is_silent=True)

        # Check phrase end detection
        is_end = pd.is_phrase_end(is_silent=True)
        # Should detect phrase end after speech followed by silence
        assert is_end is True


class TestSystemStartup:
    """Tests for system startup."""

    def test_imports_without_errors(self):
        """Test all modules import without errors."""
        import_tests = [
            "from shared import config",
            "from shared.context import AppContext",
            "from core.voice_detector import VoiceDetector",
            "from core.phrase_detector import PhraseEndDetector",
            "from core.speaker_detector import SpeakerVerifier",
            "from core.noise_reduction import reduce_noise",
            "from core.audio_preprocessing import preprocess_audio",
            "from core.models import transcribe_preview, transcribe_production",
            "from core.processor import run",
        ]

        for import_stmt in import_tests:
            try:
                exec(import_stmt)
            except Exception as e:
                pytest.fail(f"Import failed: {import_stmt} - {e}")

    def test_context_initialization(self):
        """Test context can be initialized."""
        from shared.context import AppContext

        ctx = AppContext()
        assert ctx is not None

    def test_voice_detector_lazy_load(self):
        """Test Silero VAD model loads lazily."""
        from core.voice_detector import VoiceDetector

        vd = VoiceDetector()
        assert vd._model_loaded is False

        # First detection should load model
        audio = np.random.randn(8000).astype(np.float32)
        vd.is_human_speech(audio)

        assert vd._model_loaded is True
