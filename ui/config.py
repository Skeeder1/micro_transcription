"""UI module configuration - Visualizer settings."""

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
