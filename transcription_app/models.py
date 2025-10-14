"""Whisper model initialization and transcription helpers."""

from __future__ import annotations

from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from . import config
from .context import AppContext


def _load_model(name: str) -> WhisperModel:
    return WhisperModel(
        name,
        device=config.DEVICE,
        compute_type=config.FLOAT_PRECISION,
        num_workers=config.MODEL_NUM_WORKERS,
    )


def init_models(ctx: AppContext) -> None:
    """Load whisper models if not loaded already."""
    with ctx.model_lock:
        if ctx.preview_model is None:
            try:
                print("📥 Chargement modèle PREVIEW...")
                ctx.preview_model = _load_model(config.PREVIEW_MODEL_PRIMARY)
                print(f"   ✅ Modèle '{config.PREVIEW_MODEL_PRIMARY}' chargé")
            except Exception as exc:
                print(
                    f"   ⚠️ Prévisualisation: fallback '{config.PREVIEW_MODEL_FALLBACK}' ({exc})"
                )
                ctx.preview_model = _load_model(config.PREVIEW_MODEL_FALLBACK)
        if ctx.production_model is None:
            print("📥 Chargement modèle PRODUCTION...")
            ctx.production_model = _load_model(config.PRODUCTION_MODEL)
            print(f"   ✅ Modèle '{config.PRODUCTION_MODEL}' chargé")


def _flatten(audio: np.ndarray) -> np.ndarray:
    return audio.flatten()


def _run_transcription(model: WhisperModel, audio: np.ndarray, *, preview: bool) -> Optional[str]:
    params = {
        "language": config.LANGUAGE,
        "temperature": config.TEMPERATURE,
    }
    if preview:
        params.update(
            beam_size=config.PREVIEW_BEAM_SIZE,
            vad_filter=config.PREVIEW_VAD_FILTER,
            condition_on_previous_text=config.PREVIEW_CONDITION_ON_PREVIOUS,
            word_timestamps=config.PREVIEW_WORD_TIMESTAMPS,
            best_of=config.PREVIEW_BEST_OF,
        )
    else:
        params.update(
            beam_size=config.PRODUCTION_BEAM_SIZE,
            vad_filter=config.PRODUCTION_VAD_FILTER,
            condition_on_previous_text=config.PRODUCTION_CONDITION_ON_PREVIOUS,
        )

    try:
        segments, _ = model.transcribe(_flatten(audio), **params)
    except Exception as exc:
        print(
            f"⚠️ Erreur transcription ({'preview' if preview else 'production'}): {exc}"
        )
        return None

    text = "".join(segment.text for segment in segments).strip()
    return text or None


def transcribe_preview(ctx: AppContext, audio: np.ndarray) -> Optional[str]:
    if ctx.preview_model is None:
        init_models(ctx)
    if ctx.preview_model is None:
        return None
    return _run_transcription(ctx.preview_model, audio, preview=True)


def transcribe_production(ctx: AppContext, audio: np.ndarray) -> Optional[str]:
    if ctx.production_model is None:
        init_models(ctx)
    if ctx.production_model is None:
        return None
    return _run_transcription(ctx.production_model, audio, preview=False)
