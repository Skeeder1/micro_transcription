"""Shared configuration - Imports and re-exports all module configs."""

from __future__ import annotations

# Import core config
from core.config import (
    APPEND_SPACE,
    BEAM_SIZE,
    BEST_OF,
    BLOCK_SECONDS,
    CONDITION_ON_PREVIOUS,
    DEVICE,
    ENABLE_PREVIEW,
    ENABLE_PRODUCTION,
    ENABLE_TRANSCRIPTION,
    ENERGY_THRESHOLD,
    EXECUTOR_MAX_WORKERS,
    FLOAT_PRECISION,
    LANGUAGE,
    MODEL_NUM_WORKERS,
    PASTE_DELAY_SECONDS,
    PREVIEW_TIMEOUT,
    PREVIEW_UPDATE_INTERVAL,
    PREVIEW_WINDOW_SECONDS,
    RESTORE_CLIPBOARD,
    SAMPLE_RATE,
    SILENCE_BLOCKS_BEFORE_FLUSH,
    TEMPERATURE,
    VAD_FILTER,
    WHISPER_MODEL,
    WORD_TIMESTAMPS,
    # Voice detection
    ENABLE_ADVANCED_VAD,
    SILERO_THRESHOLD,
    USE_ZCR_FILTER,
    ZCR_MIN,
    ZCR_MAX,
    DEBUG_VAD,
    USE_ADAPTIVE_DETECTION,
    ADAPTIVE_BOOST_FACTOR,
    ADAPTIVE_WINDOW_SECONDS,
    DEBUG_AUDIO_LEVEL,
    # Buffer limits
    MAX_PRODUCTION_SECONDS,
    MAX_PRODUCTION_BLOCKS,
    # Noise reduction
    ENABLE_NOISE_REDUCTION,
    NOISE_REDUCTION_STRENGTH,
    NOISE_STATIONARY,
    # Whisper prompts
    INITIAL_PROMPT,
    VOCABULARY_BOOST,
    # Phrase detection
    ENABLE_PHRASE_DETECTION,
    ENERGY_DROP_THRESHOLD,
    ENERGY_HISTORY_BLOCKS,
    # Speaker verification
    ENABLE_SPEAKER_VERIFICATION,
    SPEAKER_SIMILARITY_THRESHOLD,
    SPEAKER_EMBEDDING_PATH,
)

# Import API config
from api.config import SSE_HOST, SSE_PORT

# Import UI config
from ui.config import (
    VISUALIZER_KILL_TIMEOUT,
    VISUALIZER_READY_DELAY,
    VISUALIZER_START_DELAY,
    VISUALIZER_STOP_TIMEOUT,
)


# ============================================================================
# SLEEP / HOTKEY - Gestion du mode veille et raccourcis clavier
# ============================================================================

# Délai d'inactivité avant activation automatique du mode veille en secondes
# 30 secondes sans parole = passage en veille (équivalent à F9 OFF)
AUTO_SLEEP_SECONDS = 30.0

# Touche de raccourci pour basculer veille/actif
# "F9" = Appui sur F9 pour activer/désactiver
HOTKEY_TOGGLE = "F9"

# Fenêtre temporelle pour détecter une séquence de touches en secondes
# 0.6s = Délai max entre pressions de touches pour une séquence
HOTKEY_SEQUENCE_WINDOW = 0.6

# Délai minimum entre deux bascules veille/actif en secondes
# 1.0s = Évite les bascules accidentelles et race conditions pendant rechargement modèles
TOGGLE_COOLDOWN_SECONDS = 1.0

# Durée en veille avant passage en veille profonde (décharge modèles)
# 1800 secondes = 30 minutes
DEEP_SLEEP_SECONDS = 1800

# Debug: active des logs additionnels pour diagnostiquer l'auto-veille
# False = logs désactivés (comportement normal)
DEBUG_AUTO_SLEEP = False

# System Tray: afficher une icône dans la barre système (Ubuntu/Linux)
# True = Icône système avec menu pour contrôler l'application
# False = Pas d'icône système (mode simple)
# NOTE: Désactivé car incompatible avec mode daemon (nécessite Qt dans processus principal)
ENABLE_SYSTEM_TRAY = False


__all__ = [
    # Core
    "ENABLE_TRANSCRIPTION",
    "ENABLE_PREVIEW",
    "ENABLE_PRODUCTION",
    "SAMPLE_RATE",
    "BLOCK_SECONDS",
    "ENERGY_THRESHOLD",
    "SILENCE_BLOCKS_BEFORE_FLUSH",
    "WHISPER_MODEL",
    "DEVICE",
    "FLOAT_PRECISION",
    "MODEL_NUM_WORKERS",
    "LANGUAGE",
    "BEAM_SIZE",
    "VAD_FILTER",
    "CONDITION_ON_PREVIOUS",
    "WORD_TIMESTAMPS",
    "BEST_OF",
    "TEMPERATURE",
    "PREVIEW_WINDOW_SECONDS",
    "PREVIEW_UPDATE_INTERVAL",
    "PREVIEW_TIMEOUT",
    "RESTORE_CLIPBOARD",
    "PASTE_DELAY_SECONDS",
    "APPEND_SPACE",
    "EXECUTOR_MAX_WORKERS",
    # Voice detection
    "ENABLE_ADVANCED_VAD",
    "SILERO_THRESHOLD",
    "USE_ZCR_FILTER",
    "ZCR_MIN",
    "ZCR_MAX",
    "DEBUG_VAD",
    "USE_ADAPTIVE_DETECTION",
    "ADAPTIVE_BOOST_FACTOR",
    "ADAPTIVE_WINDOW_SECONDS",
    "DEBUG_AUDIO_LEVEL",
    # Buffer limits
    "MAX_PRODUCTION_SECONDS",
    "MAX_PRODUCTION_BLOCKS",
    # Noise reduction
    "ENABLE_NOISE_REDUCTION",
    "NOISE_REDUCTION_STRENGTH",
    "NOISE_STATIONARY",
    # Whisper prompts
    "INITIAL_PROMPT",
    "VOCABULARY_BOOST",
    # Phrase detection
    "ENABLE_PHRASE_DETECTION",
    "ENERGY_DROP_THRESHOLD",
    "ENERGY_HISTORY_BLOCKS",
    # Speaker verification
    "ENABLE_SPEAKER_VERIFICATION",
    "SPEAKER_SIMILARITY_THRESHOLD",
    "SPEAKER_EMBEDDING_PATH",
    # API
    "SSE_PORT",
    "SSE_HOST",
    # UI
    "VISUALIZER_READY_DELAY",
    "VISUALIZER_START_DELAY",
    "VISUALIZER_STOP_TIMEOUT",
    "VISUALIZER_KILL_TIMEOUT",
    # Shared
    "AUTO_SLEEP_SECONDS",
    "HOTKEY_TOGGLE",
    "HOTKEY_SEQUENCE_WINDOW",
    "TOGGLE_COOLDOWN_SECONDS",
    "DEEP_SLEEP_SECONDS",
    "DEBUG_AUTO_SLEEP",
    "ENABLE_SYSTEM_TRAY",
]
