#!/usr/bin/env python3
"""Demonstration du pipeline complet a partir d'un fichier audio, sans micro.

Pousse un WAV 16 kHz mono dans les VRAIS composants de l'application:

    WAV -> VoiceDetector (Silero VAD) -> preprocess_audio -> Whisper -> texte

Utile pour verifier une installation, mesurer les performances, ou faire
tourner le projet sur une machine sans peripherique d'entree audio.

Usage:
    python scripts/demo_pipeline.py chemin/vers/audio.wav
    python scripts/demo_pipeline.py --generate          # synthetise l'audio

Options:
    --generate      Fabrique une phrase parlee avec ffmpeg (filtre flite)
    --model NOM     Modele Whisper (defaut: small)
    --language CODE Langue de transcription (defaut: en)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEMO_PHRASE = "This project turns your voice into text and pastes it wherever your cursor is."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("wav", nargs="?", help="fichier WAV 16 kHz mono")
    parser.add_argument("--generate", action="store_true",
                        help="synthetise une phrase avec ffmpeg (filtre flite)")
    parser.add_argument("--model", default="small", help="modele Whisper (defaut: small)")
    parser.add_argument("--language", default="en", help="langue (defaut: en)")
    return parser.parse_args()


def generate_wav(destination: Path, sample_rate: int) -> Path:
    """Synthetise DEMO_PHRASE avec ffmpeg."""
    print(f"Synthese de la phrase de demonstration avec ffmpeg...")
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
            "-i", f"flite=text='{DEMO_PHRASE}':voice=slt",
            "-ar", str(sample_rate), "-ac", "1", str(destination), "-y",
        ],
        check=True, timeout=120,
    )
    return destination


def load_wav(path: Path, expected_rate: int):
    import numpy as np

    with wave.open(str(path), "rb") as handle:
        if handle.getframerate() != expected_rate:
            sys.exit(f"Erreur: {path} est a {handle.getframerate()} Hz, "
                     f"attendu {expected_rate} Hz.")
        if handle.getnchannels() != 1:
            sys.exit(f"Erreur: {path} n'est pas mono.")
        raw = handle.readframes(handle.getnframes())

    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def main() -> int:
    args = parse_args()

    # Doit etre pose avant l'import de shared.config: les settings sont
    # instancies au chargement du module.
    os.environ.setdefault("TRANSCRIBE_MODEL__WHISPER_MODEL", args.model)
    os.environ.setdefault("TRANSCRIBE_MODEL__LANGUAGE", args.language)

    import numpy as np

    from shared import config
    from shared.context import AppContext
    from core.audio_preprocessing import preprocess_audio
    from core.models import init_models, transcribe_production
    from core.voice_detector import VoiceDetector

    tempdir = None
    if args.generate or not args.wav:
        tempdir = tempfile.TemporaryDirectory()
        wav_path = generate_wav(Path(tempdir.name) / "demo.wav", config.SAMPLE_RATE)
    else:
        wav_path = Path(args.wav)
        if not wav_path.exists():
            sys.exit(f"Erreur: fichier introuvable: {wav_path}")

    audio = load_wav(wav_path, config.SAMPLE_RATE)

    print("=" * 70)
    print("DEMONSTRATION DU PIPELINE DE TRANSCRIPTION (sans micro)")
    print("=" * 70)
    print(f"Fichier   : {wav_path.name}")
    print(f"Duree     : {len(audio) / config.SAMPLE_RATE:.2f} s "
          f"({len(audio)} echantillons a {config.SAMPLE_RATE} Hz)")
    print(f"Modele    : {config.WHISPER_MODEL}  |  langue: {config.LANGUAGE}")
    print(f"Device    : {config.DEVICE} / {config.FLOAT_PRECISION}")
    print()

    # --- 1. Detection d'activite vocale ------------------------------------
    print("[1] DETECTION D'ACTIVITE VOCALE  (Silero VAD + taux de passage par zero)")
    detector = VoiceDetector(
        sample_rate=config.SAMPLE_RATE,
        silero_threshold=config.SILERO_THRESHOLD,
        rms_threshold=config.ENERGY_THRESHOLD,
        use_zcr_filter=config.USE_ZCR_FILTER,
        # Un fichier n'a pas de bruit ambiant a apprendre: la calibration
        # adaptative fausserait les premiers blocs.
        use_adaptive=False,
    )
    detector.preload_model()

    block = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)
    voiced = 0
    count = 0
    for start in range(0, len(audio) - block + 1, block):
        is_voice = detector.is_human_speech(audio[start:start + block])
        metrics = detector.get_metrics()
        count += 1
        voiced += int(is_voice)
        print(f"    bloc {count:2d} @ {start / config.SAMPLE_RATE:5.2f}s : "
              f"{'VOIX   ' if is_voice else 'silence'}  "
              f"silero={metrics['silero_probability']:.3f}  "
              f"rms={metrics['rms']:.4f}")
    print(f"    -> {voiced}/{count} blocs classes comme parole")
    print()

    # --- 2. Preprocessing ---------------------------------------------------
    print("[2] PREPROCESSING  (passe-haut 80 Hz -> amplification -> normalisation)")
    started = time.perf_counter()
    processed = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)
    elapsed_pre = time.perf_counter() - started
    print(f"    RMS avant : {float(np.sqrt(np.mean(audio ** 2))):.4f}")
    print(f"    RMS apres : {float(np.sqrt(np.mean(processed ** 2))):.4f}")
    print(f"    Duree     : {elapsed_pre * 1000:.1f} ms")
    print()

    # --- 3. Transcription ---------------------------------------------------
    print("[3] TRANSCRIPTION WHISPER")
    ctx = AppContext()
    try:
        started = time.perf_counter()
        init_models(ctx)
        elapsed_load = time.perf_counter() - started
        if ctx.model is None:
            print("    Aucun modele n'a pu etre charge.")
            return 1
        print(f"    Chargement du modele : {elapsed_load:.2f} s")

        started = time.perf_counter()
        text = transcribe_production(ctx, processed)
        elapsed_tx = time.perf_counter() - started
        ratio = (len(audio) / config.SAMPLE_RATE) / elapsed_tx if elapsed_tx else 0.0
        print(f"    Transcription        : {elapsed_tx:.2f} s  "
              f"(x{ratio:.1f} par rapport au temps reel)")
    finally:
        ctx.shutdown()
        if tempdir is not None:
            tempdir.cleanup()

    print()
    print("=" * 70)
    print(f"TEXTE TRANSCRIT : {text!r}")
    print("=" * 70)
    return 0 if text else 1


if __name__ == "__main__":
    sys.exit(main())
