"""Whisper model initialization and transcription helpers."""

from __future__ import annotations

import gc
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from shared import config
from shared.context import AppContext


def _load_model(name: str) -> WhisperModel:
    return WhisperModel(
        name,
        device=config.DEVICE,
        compute_type=config.FLOAT_PRECISION,
        num_workers=config.MODEL_NUM_WORKERS,
    )


def init_models(ctx: AppContext) -> None:
    """Load whisper model if not loaded already."""
    # Skip si transcription désactivée
    if not config.ENABLE_TRANSCRIPTION:
        print("ℹ️  Transcription désactivée - Aucun modèle chargé")
        return

    with ctx.model_lock:
        # Charger un seul modèle pour tout (preview et production)
        if ctx.model is None:
            print(f"📥 Chargement modèle Whisper '{config.WHISPER_MODEL}'...")
            ctx.model = _load_model(config.WHISPER_MODEL)
            print(f"   ✅ Modèle '{config.WHISPER_MODEL}' chargé")


def unload_models(ctx: AppContext) -> None:
    """Unload whisper model to free memory (deep sleep mode)."""
    with ctx.model_lock:
        if ctx.model is not None:
            print("🗑️  Déchargement modèle Whisper...")
            del ctx.model
            ctx.model = None
            print("   ✅ Modèle déchargé")

        # Force garbage collection pour libérer immédiatement la mémoire
        gc.collect()
        print("   ✅ Mémoire libérée")


def _flatten(audio: np.ndarray) -> np.ndarray:
    return audio.flatten()


def _run_transcription(model: WhisperModel, audio: np.ndarray) -> Optional[str]:
    """Run transcription with the unified model configuration."""
    params = {
        "language": config.LANGUAGE,
        "temperature": config.TEMPERATURE,
        "beam_size": config.BEAM_SIZE,
        "vad_filter": config.VAD_FILTER,
        "condition_on_previous_text": config.CONDITION_ON_PREVIOUS,
        "word_timestamps": config.WORD_TIMESTAMPS,
        "best_of": config.BEST_OF,
    }

    try:
        segments, _ = model.transcribe(_flatten(audio), **params)
    except Exception as exc:
        print(f"⚠️ Erreur transcription: {exc}")
        return None

    text = "".join(segment.text for segment in segments).strip()
    return text or None


def transcribe_preview(ctx: AppContext, audio: np.ndarray) -> Optional[str]:
    """Transcribe audio for preview using the main model."""
    if ctx.model is None:
        init_models(ctx)
    if ctx.model is None:
        return None
    return _run_transcription(ctx.model, audio)


def transcribe_production(ctx: AppContext, audio: np.ndarray) -> Optional[str]:
    """Transcribe audio for production using the main model."""
    if ctx.model is None:
        init_models(ctx)
    if ctx.model is None:
        return None
    return _run_transcription(ctx.model, audio)
