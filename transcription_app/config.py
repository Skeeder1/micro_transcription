"""Application-wide configuration constants."""

# ============================================================================
# FEATURE FLAGS - Activation/Désactivation des fonctionnalités
# ============================================================================

# Active ou désactive toute la transcription (modèles IA)
# False = Mode visualiseur uniquement (pas de chargement de modèles)
ENABLE_TRANSCRIPTION = True

# Active la transcription en temps réel affichée dans le visualiseur
# DÉSACTIVÉ = Pas de prévisualisation, transcription directe au curseur uniquement
ENABLE_PREVIEW = False

# Active la transcription finale collée dans le presse-papiers
# True = Transcription directe avec modèle large au curseur
ENABLE_PRODUCTION = True


# ============================================================================
# AUDIO - Configuration de capture et détection audio
# ============================================================================

# Taux d'échantillonnage audio en Hz (16000 = qualité Whisper optimale)
SAMPLE_RATE = 16000

# Durée de chaque bloc audio capturé en secondes
BLOCK_SECONDS = 0.5

# Seuil d'énergie pour détecter de la parole (0.001-0.01 recommandé)
# Plus bas = plus sensible, détecte les chuchotements
ENERGY_THRESHOLD = 0.003

# Nombre de blocs silencieux avant de finaliser la transcription
# 3 blocs * 0.5s = 1.5 seconde de silence minimum
SILENCE_BLOCKS_BEFORE_FLUSH = 3


# ============================================================================
# MODELS - Configuration des modèles Whisper
# ============================================================================

# Modèle Whisper unique utilisé pour toute transcription
# "large" = Meilleure qualité (utilisé pour preview ET production)
WHISPER_MODEL = "large"

# Périphérique de calcul: "cuda" (GPU NVIDIA) ou "cpu"
DEVICE = "cuda"

# Précision des calculs: "float16" (GPU) ou "float32" (CPU)
# float16 = 2x plus rapide avec GPU compatible
FLOAT_PRECISION = "float16"

# Nombre de threads pour le chargement du modèle
MODEL_NUM_WORKERS = 2

# Langue de transcription (fr/en/es/de/it...)
LANGUAGE = "fr"

# Taille du faisceau de recherche (1-10)
# Plus élevé = meilleure qualité mais plus lent
BEAM_SIZE = 5

# Filtre VAD (Voice Activity Detection)
# True = Ignore les segments sans parole
VAD_FILTER = True

# Conditionner sur le texte précédent
# True = Meilleure cohérence du texte
CONDITION_ON_PREVIOUS = True

# Générer les timestamps de mots
# False = Plus rapide
WORD_TIMESTAMPS = False

# Nombre de candidats à évaluer (1-5)
# Plus élevé = meilleure qualité mais plus lent
BEST_OF = 2

# Température de sampling (0.0-1.0)
# 0.0 = Déterministe et précis (recommandé)
TEMPERATURE = 0.0


# ============================================================================
# PREVIEW - Configuration de l'aperçu temps réel
# ============================================================================

# Durée de la fenêtre glissante d'audio pour la preview en secondes
# 3 secondes = Contexte suffisant sans trop de latence
PREVIEW_WINDOW_SECONDS = 3.0

# Intervalle minimum entre deux mises à jour de preview en secondes
# 1 seconde = Mise à jour fluide sans surcharger le GPU
PREVIEW_UPDATE_INTERVAL = 1.0

# Timeout maximum pour une transcription preview en secondes
# Si dépassé, la preview est ignorée
PREVIEW_TIMEOUT = 8.0


# ============================================================================
# PRODUCTION - Configuration de la transcription finale
# ============================================================================

# Restaurer le contenu original du presse-papiers après collage
# True = Le presse-papiers garde son contenu précédent
RESTORE_CLIPBOARD = True

# Délai avant de coller le texte transcrit en secondes
# 0.05s = Temps pour que l'application cible soit prête
PASTE_DELAY_SECONDS = 0.05

# Ajouter un espace après le texte collé
# True = Prêt pour continuer à taper
APPEND_SPACE = True


# ============================================================================
# SERVER - Configuration du serveur SSE (Server-Sent Events)
# ============================================================================

# Port du serveur SSE pour communication avec le visualiseur
SSE_PORT = 5432

# Adresse IP du serveur SSE (127.0.0.1 = localhost uniquement)
SSE_HOST = "127.0.0.1"


# ============================================================================
# SLEEP / HOTKEY - Gestion du mode veille et raccourcis clavier
# ============================================================================

# Délai d'inactivité avant activation automatique du mode veille en secondes
# 10 secondes sans parole = passage en veille
AUTO_SLEEP_SECONDS = 10.0

# Touche de raccourci pour basculer veille/actif
# "F9" = Appui sur F9 pour activer/désactiver
HOTKEY_TOGGLE = "F9"

# Fenêtre temporelle pour détecter une séquence de touches en secondes
# 0.6s = Délai max entre pressions de touches pour une séquence
HOTKEY_SEQUENCE_WINDOW = 0.6

# Délai minimum entre deux bascules veille/actif en secondes
# 0.3s = Évite les bascules accidentelles trop rapides
TOGGLE_COOLDOWN_SECONDS = 0.3

# Durée en veille avant passage en veille profonde (décharge modèles)
# 600 secondes = 10 minutes
DEEP_SLEEP_SECONDS = 600


# ============================================================================
# VISUALIZER - Configuration du visualiseur d'ondes
# ============================================================================

# Délai d'attente pour que le visualiseur soit prêt en secondes
# 0.3s = Temps de chargement de l'interface graphique
VISUALIZER_READY_DELAY = 0.3

# Délai après démarrage du visualiseur avant utilisation en secondes
# 0.2s = Temps d'initialisation de WaveSurfer
VISUALIZER_START_DELAY = 0.2

# Timeout pour l'arrêt gracieux du visualiseur en secondes
# 2s = Temps max pour fermeture propre avant kill forcé
VISUALIZER_STOP_TIMEOUT = 2.0

# Timeout pour le kill forcé du visualiseur en secondes
# 1s = Temps max avant abandon du kill
VISUALIZER_KILL_TIMEOUT = 1.0


# ============================================================================
# MISC - Paramètres divers
# ============================================================================

# Nombre maximum de workers pour le pool d'exécution parallèle
# 2 workers = Preview + Production peuvent tourner en parallèle
EXECUTOR_MAX_WORKERS = 2
