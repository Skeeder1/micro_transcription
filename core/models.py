"""Whisper model initialization and transcription helpers.

This module handles:
- Model loading with automatic device detection and fallback
- Transcription for both preview and production modes
- Hallucination filtering to reduce Whisper artifacts

Uses the centralized error handling system for consistent error management.
"""

from __future__ import annotations

import gc
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

from shared import config
from shared.audio_utils import validate_audio
from shared.constants import LOG_PREFIX_FILTER, LOG_PREFIX_WHISPER
from shared.context import AppContext
from shared.errors import (
    ModelLoadError,
    handle_errors,
)
from shared.events import EventBus, Events
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
        ModelLoadError: Si le chargement échoue
    """
    log_info(f"Chargement modèle '{name}' sur device '{device}'...")

    try:
        model = WhisperModel(
            name,
            device=device,
            compute_type=config.FLOAT_PRECISION if device == "cuda" else "int8",
            num_workers=config.MODEL_NUM_WORKERS,
        )
        log_info(f"   Modèle '{name}' chargé avec succès")
        return model
    except Exception as exc:
        error_msg = f"Échec chargement modèle '{name}' sur '{device}': {exc}"
        log_error(f"   {error_msg}")
        raise ModelLoadError(error_msg, cause=exc) from exc


@handle_errors(log_prefix="[Models]", reraise=True)
def init_models(ctx: AppContext) -> None:
    """Load whisper model if not loaded already.

    Détecte automatiquement CUDA/CPU et fait des fallbacks si nécessaire:
    1. Essaie le modèle configuré sur le device détecté
    2. Si échec, essaie modèle "medium" (plus léger)
    3. Si échec, essaie modèle "small" (très léger)
    4. Si échec, lève une exception

    Publishes:
        - MODEL_LOADING_STARTED: When model loading begins
        - MODEL_LOADING_COMPLETE: When model loaded successfully
        - MODEL_LOADING_FAILED: When all loading attempts fail

    Raises:
        ModelLoadError: Si aucun modèle n'a pu être chargé
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

        # Publish loading started event
        EventBus.publish(Events.MODEL_LOADING_STARTED, model=config.WHISPER_MODEL)

        # Détecter le device disponible
        device = _detect_device()

        # Liste des modèles à essayer (du plus lourd au plus léger)
        models_to_try = [config.WHISPER_MODEL]
        if config.WHISPER_MODEL not in ["medium", "small"]:
            models_to_try.append("medium")  # Fallback 1
        if "small" not in models_to_try:
            models_to_try.append("small")  # Fallback 2

        # Essayer de charger les modèles dans l'ordre
        last_error: Optional[Exception] = None
        for model_name in models_to_try:
            try:
                ctx.model = _load_model(model_name, device)
                if model_name != config.WHISPER_MODEL:
                    log_warn(f"Utilisation du modèle de fallback '{model_name}' au lieu de '{config.WHISPER_MODEL}'")

                # Publish loading complete event
                EventBus.publish(
                    Events.MODEL_LOADING_COMPLETE,
                    model=model_name,
                    device=device,
                    is_fallback=(model_name != config.WHISPER_MODEL)
                )
                return  # Succès !
            except ModelLoadError as exc:
                last_error = exc
                log_error(f"   Échec: {exc}")
                if model_name == models_to_try[-1]:
                    # C'était le dernier modèle, échec total
                    log_error("ÉCHEC TOTAL: Aucun modèle Whisper n'a pu être chargé")

                    # Publish loading failed event
                    EventBus.publish(
                        Events.MODEL_LOADING_FAILED,
                        error=str(exc),
                        attempted_models=models_to_try
                    )

                    raise ModelLoadError(
                        f"Impossible de charger un modèle Whisper. Dernier essai: {model_name}",
                        cause=last_error
                    ) from exc
                else:
                    log_warn(f"   Tentative de fallback sur modèle plus léger...")


@handle_errors(log_prefix="[Models]", reraise=False)
def unload_models(ctx: AppContext) -> None:
    """Unload whisper model to free memory (deep sleep mode).

    Publishes:
        - MODEL_UNLOADED: When model is successfully unloaded
    """
    with ctx.model_lock:
        if ctx.model is not None:
            log_info("🗑️  Déchargement modèle Whisper...")
            del ctx.model
            ctx.model = None
            log_info("   ✅ Modèle déchargé")

            # Publish model unloaded event
            EventBus.publish(Events.MODEL_UNLOADED)

        # Force garbage collection pour libérer immédiatement la mémoire
        gc.collect()
        log_info("   ✅ Mémoire libérée")


# =============================================================================
# Filtre anti-hallucinations Whisper
# =============================================================================

# Phrases typiques que Whisper génère quand il reçoit du bruit/silence
# NOTE: Ces patterns sont vérifiés comme phrases complètes OU comme sous-chaînes
#       selon leur catégorie (voir _is_hallucination)

# Patterns qui doivent être le texte COMPLET (ou presque) pour être filtrés
HALLUCINATION_EXACT_PATTERNS = [
    # Musique/Son - seulement si c'est le seul contenu
    "musique",
    "♪",
    "applaudissements",
    "rires",
    "silence",
    "...",
    ".",
    # Phrases courtes vides
    "je vous remercie",
    "merci",
    "bonne journée",
    "bonne soirée",
    "à bientôt",
    "à la prochaine",
]

# Patterns qui peuvent être des sous-chaînes (phrases plus longues/spécifiques)
HALLUCINATION_SUBSTRING_PATTERNS = [
    # Sous-titres YouTube/TV
    "sous-titrage",
    "sous-titres",
    "société radio-canada",
    "sous-titres par",
    "sous-titrage st",

    # Remerciements vidéo typiques
    "merci d'avoir regardé",
    "merci d'avoir écouté",
    "merci à mes tipeurs",
    "merci à mes souscripteurs",
    "n'hésitez pas à vous abonner",
    "likez la vidéo",
    "laissez un commentaire",
    "c'est tout pour aujourd'hui",

    # Anglais courant
    "thank you for watching",
    "thanks for watching",
    "like and subscribe",
]


def _is_hallucination(text: str) -> bool:
    """
    Vérifie si le texte est une hallucination typique de Whisper.

    Args:
        text: Texte transcrit

    Returns:
        True si c'est probablement une hallucination
    """
    if not text:
        return True

    text_lower = text.lower().strip()

    # Patterns exacts : le texte doit être UNIQUEMENT ce pattern (ou très court)
    # Permet de dire "j'aime la musique" sans être filtré
    if len(text_lower) < 30:  # Seulement pour les textes courts
        for pattern in HALLUCINATION_EXACT_PATTERNS:
            if text_lower == pattern or text_lower == pattern + ".":
                log_info(f"{LOG_PREFIX_FILTER} Hallucination exacte: '{text}'")
                return True

    # Patterns substring : peuvent être n'importe où dans le texte
    # (phrases spécifiques de YouTube/vidéo)
    for pattern in HALLUCINATION_SUBSTRING_PATTERNS:
        if pattern in text_lower:
            log_info(f"{LOG_PREFIX_FILTER} Hallucination détectée: '{pattern}' dans '{text[:50]}...'")
            return True

    # Texte répétitif (même mot/phrase répété)
    words = text_lower.split()
    if len(words) >= 6:  # Augmenté de 4 à 6 pour éviter faux positifs
        unique_words = set(words)
        ratio = len(unique_words) / len(words)
        # Seuil abaissé de 0.4 à 0.25 (plus permissif)
        if ratio < 0.25:
            log_warn(f"{LOG_PREFIX_FILTER} Texte répétitif rejeté ({ratio:.0%} unique): '{text[:80]}...'")
            return True

    return False


def _filter_hallucinations(text: Optional[str]) -> Optional[str]:
    """
    Filtre les hallucinations de la transcription.

    Args:
        text: Texte transcrit

    Returns:
        Texte filtré ou None si hallucination
    """
    if text is None:
        return None

    if _is_hallucination(text):
        return None

    return text


def _flatten(audio: np.ndarray) -> np.ndarray:
    return audio.flatten()


@handle_errors(log_prefix=LOG_PREFIX_WHISPER, reraise=False, default_return=None)
def _run_transcription(model: WhisperModel, audio: np.ndarray) -> Optional[str]:
    """Run transcription with the unified model configuration.

    Uses the centralized error handling decorator for consistent error management.
    Returns None on any error to allow graceful degradation.
    """
    # Validate and normalize audio
    try:
        audio_flat = validate_audio(_flatten(audio), min_length=512)
    except ValueError as e:
        log_warn(f"{LOG_PREFIX_WHISPER} Audio invalide: {e}")
        return None

    # Debug: log audio stats
    duration_sec = len(audio_flat) / config.SAMPLE_RATE
    audio_rms = np.sqrt(np.mean(np.square(audio_flat), dtype=np.float64))
    log_info(f"{LOG_PREFIX_WHISPER} Audio: {duration_sec:.2f}s, RMS={audio_rms:.4f}, samples={len(audio_flat)}")

    # Build initial prompt from config
    initial_prompt = getattr(config, 'INITIAL_PROMPT', None)

    # Add vocabulary boost words to prompt if available
    vocab_boost = getattr(config, 'VOCABULARY_BOOST', [])
    if vocab_boost and initial_prompt:
        initial_prompt = initial_prompt + "\nVocabulaire: " + ", ".join(vocab_boost)

    params = {
        "language": config.LANGUAGE,
        "temperature": config.TEMPERATURE,
        "beam_size": config.BEAM_SIZE,
        "vad_filter": config.VAD_FILTER,
        "condition_on_previous_text": config.CONDITION_ON_PREVIOUS,
        "word_timestamps": config.WORD_TIMESTAMPS,
        "best_of": config.BEST_OF,
    }

    # Add initial prompt if configured
    if initial_prompt:
        params["initial_prompt"] = initial_prompt

    # Run transcription with error handling
    try:
        segments, info = model.transcribe(audio_flat, **params)
        segments_list = list(segments)  # Consommer le générateur
        log_info(f"{LOG_PREFIX_WHISPER} Got {len(segments_list)} segments, language={info.language}, prob={info.language_probability:.2f}")
    except Exception as exc:
        # Log error but don't raise - return None for graceful degradation
        log_warn(f"{LOG_PREFIX_WHISPER} Erreur transcription: {exc}")
        return None

    text = "".join(segment.text for segment in segments_list).strip()
    log_info(f"{LOG_PREFIX_WHISPER} Result: '{text[:50] if text else '(empty)'}...'")
    return text or None


@handle_errors(log_prefix="[Preview]", reraise=False, default_return=None)
def transcribe_preview(ctx: AppContext, audio: np.ndarray) -> Optional[str]:
    """Transcribe audio for preview using the main model.

    Uses error handling decorator for graceful degradation on failures.
    Returns None if model not loaded or transcription fails.
    """
    if ctx.model is None:
        init_models(ctx)
    if ctx.model is None:
        return None
    text = _run_transcription(ctx.model, audio)
    return _filter_hallucinations(text)


@handle_errors(log_prefix="[Production]", reraise=False, default_return=None)
def transcribe_production(ctx: AppContext, audio: np.ndarray) -> Optional[str]:
    """Transcribe audio for production using the main model.

    Uses error handling decorator for graceful degradation on failures.
    Returns None if model not loaded or transcription fails.
    """
    if ctx.model is None:
        init_models(ctx)
    if ctx.model is None:
        return None
    text = _run_transcription(ctx.model, audio)
    return _filter_hallucinations(text)
