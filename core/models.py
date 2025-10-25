"""Whisper model initialization and transcription helpers."""

from __future__ import annotations

import gc
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from shared import config
from shared.context import AppContext
from shared.logger import log_info, log_warn, log_error


def _detect_device() -> str:
    """Détecter le device disponible (CUDA ou CPU).

    Returns:
        "cuda" si GPU NVIDIA disponible, sinon "cpu"
    """
    # Si config demande CPU explicitement
    if config.DEVICE == "cpu":
        log_info("📟 Device: CPU (configuré explicitement)")
        return "cpu"

    # Essayer CUDA
    if config.DEVICE == "cuda":
        try:
            import torch
            if torch.cuda.is_available():
                log_info("🎮 Device: CUDA (GPU NVIDIA détecté)")
                return "cuda"
            else:
                log_warn("⚠️ CUDA demandé mais GPU non disponible - Fallback CPU")
                return "cpu"
        except ImportError:
            log_warn("⚠️ PyTorch non installé - Impossible de vérifier CUDA - Fallback CPU")
            return "cpu"
        except Exception as exc:
            log_warn(f"⚠️ Erreur lors de la détection CUDA: {exc} - Fallback CPU")
            return "cpu"

    # Device inconnu
    log_warn(f"⚠️ Device '{config.DEVICE}' inconnu - Fallback CPU")
    return "cpu"


def _load_model(name: str, device: str) -> WhisperModel:
    """Charger un modèle Whisper avec gestion d'erreurs.

    Args:
        name: Nom du modèle (tiny, base, small, medium, large)
        device: Device à utiliser (cuda ou cpu)

    Returns:
        Modèle Whisper chargé

    Raises:
        Exception: Si le chargement échoue
    """
    log_info(f"📥 Chargement modèle '{name}' sur device '{device}'...")

    try:
        model = WhisperModel(
            name,
            device=device,
            compute_type=config.FLOAT_PRECISION if device == "cuda" else "int8",
            num_workers=config.MODEL_NUM_WORKERS,
        )
        log_info(f"   ✅ Modèle '{name}' chargé avec succès")
        return model
    except Exception as exc:
        log_error(f"   ❌ Échec chargement modèle '{name}' sur '{device}': {exc}")
        raise


def init_models(ctx: AppContext) -> None:
    """Load whisper model if not loaded already.

    Détecte automatiquement CUDA/CPU et fait des fallbacks si nécessaire:
    1. Essaie le modèle configuré sur le device détecté
    2. Si échec, essaie modèle "medium" (plus léger)
    3. Si échec, essaie modèle "small" (très léger)
    4. Si échec, lève une exception

    Raises:
        Exception: Si aucun modèle n'a pu être chargé
    """
    # Skip si transcription désactivée
    if not config.ENABLE_TRANSCRIPTION:
        log_info("ℹ️  Transcription désactivée - Aucun modèle chargé")
        return

    with ctx.model_lock:
        # Charger un seul modèle pour tout (preview et production)
        if ctx.model is not None:
            log_info("ℹ️  Modèle déjà chargé, skip")
            return

        # Détecter le device disponible
        device = _detect_device()

        # Liste des modèles à essayer (du plus lourd au plus léger)
        models_to_try = [config.WHISPER_MODEL]
        if config.WHISPER_MODEL not in ["medium", "small"]:
            models_to_try.append("medium")  # Fallback 1
        if "small" not in models_to_try:
            models_to_try.append("small")  # Fallback 2

        # Essayer de charger les modèles dans l'ordre
        for model_name in models_to_try:
            try:
                ctx.model = _load_model(model_name, device)
                if model_name != config.WHISPER_MODEL:
                    log_warn(f"⚠️ Utilisation du modèle de fallback '{model_name}' au lieu de '{config.WHISPER_MODEL}'")
                return  # Succès !
            except Exception as exc:
                log_error(f"   ❌ Échec: {exc}")
                if model_name == models_to_try[-1]:
                    # C'était le dernier modèle, échec total
                    log_error("❌ ÉCHEC TOTAL: Aucun modèle Whisper n'a pu être chargé")
                    raise Exception(f"Impossible de charger un modèle Whisper. Dernier essai: {model_name}") from exc
                else:
                    log_warn(f"   ⚠️ Tentative de fallback sur modèle plus léger...")


def unload_models(ctx: AppContext) -> None:
    """Unload whisper model to free memory (deep sleep mode)."""
    with ctx.model_lock:
        if ctx.model is not None:
            log_info("🗑️  Déchargement modèle Whisper...")
            del ctx.model
            ctx.model = None
            log_info("   ✅ Modèle déchargé")

        # Force garbage collection pour libérer immédiatement la mémoire
        gc.collect()
        log_info("   ✅ Mémoire libérée")


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
        log_warn(f"⚠️ Erreur transcription: {exc}")
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
