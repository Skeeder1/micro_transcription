"""Tests bout-en-bout du pipeline, sans micro physique.

L'application est concue autour d'un micro live, ce qui la rend difficile a
tester en CI. Ces tests contournent le probleme en synthetisant de la parole
avec ffmpeg (filtre `flite`) et en la poussant dans le VRAI pipeline:

    WAV -> VoiceDetector (Silero VAD) -> preprocess_audio -> Whisper

Les tests qui chargent Whisper sont marques `slow` (modele a telecharger,
inference GPU/CPU). Pour la suite rapide:

    pytest -m "not slow"
"""

from __future__ import annotations

import shutil
import subprocess
import wave

import numpy as np
import pytest

from shared import config

PHRASE = "The quick brown fox jumps over the lazy dog."


def _ffmpeg_has_flite() -> bool:
    """flite est optionnel dans ffmpeg: il faut verifier sa presence."""
    if shutil.which("ffmpeg") is None:
        return False
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-filters"],
        capture_output=True, text=True, timeout=30,
    )
    return "flite" in probe.stdout


requires_flite = pytest.mark.skipif(
    not _ffmpeg_has_flite(),
    reason="ffmpeg avec le filtre flite est requis pour synthetiser la parole",
)


@pytest.fixture(scope="session")
def spoken_wav(tmp_path_factory):
    """Synthetise une phrase parlee en WAV 16 kHz mono."""
    path = tmp_path_factory.mktemp("audio") / "phrase.wav"
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"flite=text='{PHRASE}':voice=slt",
            "-ar", str(config.SAMPLE_RATE), "-ac", "1",
            str(path), "-y",
        ],
        check=True, timeout=120,
    )
    return path


@pytest.fixture(scope="session")
def spoken_audio(spoken_wav):
    """Charge le WAV en float32 [-1, 1], comme le ferait sounddevice."""
    with wave.open(str(spoken_wav), "rb") as handle:
        assert handle.getframerate() == config.SAMPLE_RATE
        assert handle.getnchannels() == 1
        raw = handle.readframes(handle.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def _blocks(audio: np.ndarray):
    """Decoupe l'audio en blocs de la meme taille que la boucle temps reel."""
    size = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)
    for start in range(0, len(audio) - size + 1, size):
        yield audio[start:start + size]


@requires_flite
class TestSynthesizedSpeechFixture:
    """Le materiau de test lui-meme doit etre valide."""

    def test_audio_is_non_trivial(self, spoken_audio):
        assert len(spoken_audio) > config.SAMPLE_RATE  # > 1 s
        assert float(np.abs(spoken_audio).max()) > 0.05
        assert np.isfinite(spoken_audio).all()


@requires_flite
class TestVoiceActivityDetection:
    """Le VAD doit separer la parole synthetisee du silence."""

    @pytest.fixture(scope="class")
    def detector(self):
        from core.voice_detector import VoiceDetector

        det = VoiceDetector(
            sample_rate=config.SAMPLE_RATE,
            silero_threshold=config.SILERO_THRESHOLD,
            rms_threshold=config.ENERGY_THRESHOLD,
            use_zcr_filter=config.USE_ZCR_FILTER,
            # Pas de calibration adaptative: un fichier n'a pas de bruit ambiant
            # a apprendre, et la calibration fausserait les premiers blocs.
            use_adaptive=False,
        )
        det.preload_model()
        return det

    def test_detects_speech_in_spoken_audio(self, detector, spoken_audio):
        results = [detector.is_human_speech(b) for b in _blocks(spoken_audio)]

        assert results, "aucun bloc analyse"
        # La synthese contient une amorce et une chute de silence: on exige la
        # majorite des blocs, pas la totalite.
        assert sum(results) >= len(results) // 2, (
            f"parole detectee dans seulement {sum(results)}/{len(results)} blocs"
        )

    def test_rejects_digital_silence(self, detector):
        size = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)
        silence = np.zeros(size, dtype=np.float32)

        assert detector.is_human_speech(silence) is False

    def test_metrics_are_populated_after_detection(self, detector, spoken_audio):
        next(_blocks(spoken_audio))
        detector.is_human_speech(next(_blocks(spoken_audio)))

        metrics = detector.get_metrics()
        assert metrics["rms"] > 0.0
        assert 0.0 <= metrics["silero_probability"] <= 1.0


@requires_flite
class TestPreprocessingOnRealSpeech:
    """Le preprocessing doit conditionner l'audio sans le detruire."""

    def test_output_is_bounded_and_finite(self, spoken_audio):
        from core.audio_preprocessing import preprocess_audio

        out = preprocess_audio(spoken_audio, sample_rate=config.SAMPLE_RATE,
                               for_production=True)

        assert out.shape == spoken_audio.shape
        assert np.isfinite(out).all()
        assert float(np.abs(out).max()) <= 1.0 + 1e-6

    def test_quiet_speech_is_amplified(self, spoken_audio):
        """Une prise de son faible doit etre remontee, pas laissee telle quelle."""
        from core.audio_preprocessing import preprocess_audio

        quiet = (spoken_audio * 0.02).astype(np.float32)
        out = preprocess_audio(quiet, sample_rate=config.SAMPLE_RATE,
                               for_production=True)

        rms_in = float(np.sqrt(np.mean(quiet ** 2)))
        rms_out = float(np.sqrt(np.mean(out ** 2)))
        assert rms_out > rms_in


@requires_flite
@pytest.mark.slow
class TestWhisperTranscription:
    """Bout-en-bout complet, Whisper compris.

    Marque `slow`: telecharge le modele au premier lancement puis fait tourner
    une inference. La langue est forcee en anglais car la voix flite disponible
    (slt) est anglophone, alors que le projet vise le francais par defaut.
    """

    def test_transcribes_synthesized_phrase(self, spoken_audio, monkeypatch):
        from core.audio_preprocessing import preprocess_audio
        from shared.context import AppContext

        monkeypatch.setattr(config, "WHISPER_MODEL", "small", raising=False)
        monkeypatch.setattr(config, "LANGUAGE", "en", raising=False)

        from core.models import init_models, transcribe_production

        ctx = AppContext()
        try:
            init_models(ctx)
            if ctx.model is None:
                pytest.skip("aucun modele Whisper n'a pu etre charge")

            audio = preprocess_audio(spoken_audio, sample_rate=config.SAMPLE_RATE,
                                     for_production=True)
            text = transcribe_production(ctx, audio)
        finally:
            ctx.shutdown()

        assert text, "Whisper n'a rien retourne"

        # On ne compare pas mot a mot (la synthese n'est pas parfaite): on
        # verifie que les mots porteurs de la phrase sont bien ressortis.
        lowered = text.lower()
        found = [w for w in ("quick", "brown", "fox", "lazy", "dog") if w in lowered]
        assert len(found) >= 3, f"transcription inattendue: {text!r} (mots trouves: {found})"
