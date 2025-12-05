"""Core transcription module configuration."""

# ============================================================================
# FEATURE FLAGS - Activation/Désactivation des fonctionnalités
# ============================================================================

# Active ou désactive toute la transcription (modèles IA)
# False = Mode visualiseur uniquement (pas de chargement de modèles)
ENABLE_TRANSCRIPTION = True

# Active la transcription en temps réel affichée dans le visualiseur
# True = Feedback instantané sur la transcription (recommandé pour tuning)
# False = Pas de prévisualisation, transcription directe au curseur uniquement (plus rapide)
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
# 0.015 = réduit bruit ambiant, empêche détection continue (permet auto-sleep)
ENERGY_THRESHOLD = 0.015

# Nombre de blocs silencieux avant de finaliser la transcription
# 2 blocs * 0.5s = 1.0 seconde de silence minimum (réduit pour latence)
SILENCE_BLOCKS_BEFORE_FLUSH = 2


# ============================================================================
# VOICE DETECTION - Détection voix humaine vs bruit ambiant
# ============================================================================

# Active la détection avancée voix/bruit avec Silero VAD
# True = Utilise Silero VAD + ZCR pour distinguer voix du bruit ambiant
# False = Utilise uniquement le seuil RMS basique (mode legacy)
ENABLE_ADVANCED_VAD = True

# Seuil de probabilité Silero VAD (0.0-1.0)
# 0.3 = Très sensible (détecte chuchotements, peut avoir faux positifs)
# 0.5 = Équilibré (recommandé, bon compromis voix/bruit)
# 0.7 = Strict (rejette plus de bruit, peut manquer parole faible)
SILERO_THRESHOLD = 0.5

# Active le filtre Zero Crossing Rate (ZCR)
# True = Filtre additionnel pour rejeter bruit blanc/sifflement
# False = Utilise uniquement Silero VAD
USE_ZCR_FILTER = True

# Plage ZCR acceptable pour la voix humaine
# En dehors de cette plage = probablement du bruit
ZCR_MIN = 0.02  # Minimum (en dessous = bourdonnement/DC offset)
ZCR_MAX = 0.30  # Maximum (au-dessus = bruit blanc/sifflement)

# Mode debug VAD - Affiche les métriques détaillées
# True = Affiche RMS, probabilité Silero, et ZCR en temps réel
DEBUG_VAD = False

# Détection adaptative (détecte la parole par-dessus le bruit ambiant)
# True = Utilise un niveau de référence adaptatif (RECOMMANDÉ pour environnements bruyants)
# False = Utilise des seuils fixes (mode legacy)
USE_ADAPTIVE_DETECTION = True

# Facteur de boost nécessaire pour détecter la voix
# Votre voix doit être X fois plus forte que le bruit ambiant
# 2.0 = Très sensible (détecte facilement, risque de faux positifs)
# 2.5 = Équilibré (recommandé pour bureau/café avec musique)
# 3.0 = Strict (nécessite voix forte, meilleur pour environnements très bruyants)
ADAPTIVE_BOOST_FACTOR = 2.5

# Durée de la fenêtre de référence pour le niveau ambiant (secondes)
# Plus court = s'adapte vite aux changements de bruit
# Plus long = plus stable, moins sensible aux variations
ADAPTIVE_WINDOW_SECONDS = 3.0


# ============================================================================
# MODELS - Configuration des modèles Whisper
# ============================================================================

# Modèle Whisper unique utilisé pour toute transcription
# "small" = Rapide sur CPU (recommandé si pas de GPU) - 2-3s de latence
# "medium" = Bon compromis qualité/vitesse (nécessite GPU ou CPU puissant)
# "large" = Meilleure qualité mais TRÈS LENT sur CPU, RAPIDE avec GPU
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
# 5 = bon compromis vitesse/qualité
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
# 1 = plus rapide (déterministe avec temperature=0.0)
BEST_OF = 1

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
# 20s pour CPU lent (TEMPORAIRE - activez le GPU pour de vraies perfs!)
PREVIEW_TIMEOUT = 20.0


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
# MISC - Paramètres divers
# ============================================================================

# Nombre maximum de workers pour le pool d'exécution parallèle
# 2 workers = Preview + Production peuvent tourner en parallèle
EXECUTOR_MAX_WORKERS = 2

# Mode debug - Affiche le niveau audio RMS en temps réel
# Utile pour diagnostiquer les problèmes de détection vocale
DEBUG_AUDIO_LEVEL = False


# ============================================================================
# BUFFER LIMITS - Protection contre accumulation mémoire
# ============================================================================

# Durée maximum d'enregistrement continu avant flush forcé (secondes)
# 30s = Protection contre parole continue sans pause
MAX_PRODUCTION_SECONDS = 30.0

# Nombre maximum de blocks dans le buffer de production
MAX_PRODUCTION_BLOCKS = int(MAX_PRODUCTION_SECONDS / BLOCK_SECONDS)


# ============================================================================
# NOISE REDUCTION - Réduction de bruit avancée
# ============================================================================

# Active la réduction de bruit par deep learning
# True = Utilise noisereduce pour supprimer bruit ambiant (aspirateur, TV, etc.)
ENABLE_NOISE_REDUCTION = True

# Niveau de réduction du bruit (0.0 à 1.0)
# 0.5 = Modéré (préserve qualité voix)
# 0.8 = Agressif (meilleur pour environnements très bruyants)
NOISE_REDUCTION_STRENGTH = 0.75

# Utiliser le mode stationnaire (bruit constant comme ventilateur)
# False = Mode non-stationnaire (bruit variable comme TV)
NOISE_STATIONARY = False


# ============================================================================
# WHISPER PROMPTS - Contexte initial pour améliorer transcription
# ============================================================================

# Prompt initial pour guider Whisper sur le contexte
INITIAL_PROMPT = """Transcription de dictée vocale en français.
Le locuteur parle clairement avec une prononciation standard."""

# Vocabulaire personnalisé (noms propres, termes techniques fréquents)
# Whisper utilisera ces mots comme indices de contexte
VOCABULARY_BOOST = [
    "Claude", "Anthropic", "Python", "JavaScript", "TypeScript",
    "Linux", "Ubuntu", "Windows", "Docker", "Git", "GitHub",
]


# ============================================================================
# PHRASE DETECTION - Détection intelligente de fin de phrase
# ============================================================================

# Active la détection intelligente de fin de phrase
# True = Combine silence + chute d'énergie + analyse prosodique
ENABLE_PHRASE_DETECTION = True

# Seuil de chute d'énergie pour détecter fin de mot/phrase (0.0 à 1.0)
# 0.3 = Chute de 70% de l'énergie = probable fin de phrase
ENERGY_DROP_THRESHOLD = 0.3

# Nombre de blocks pour calculer la tendance d'énergie
ENERGY_HISTORY_BLOCKS = 5


# ============================================================================
# SPEAKER VERIFICATION - Distinction voix utilisateur vs autres
# ============================================================================

# Active la vérification du locuteur
# True = Ne transcrit que la voix de l'utilisateur enregistré
ENABLE_SPEAKER_VERIFICATION = False  # Désactivé par défaut (nécessite enregistrement)

# Seuil de similarité pour accepter la voix (0.0 à 1.0)
# 0.7 = 70% de similarité minimum avec l'empreinte enregistrée
SPEAKER_SIMILARITY_THRESHOLD = 0.7

# Chemin vers le fichier d'empreinte vocale
SPEAKER_EMBEDDING_PATH = "data/user_embedding.npy"
