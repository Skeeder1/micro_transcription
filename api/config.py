"""API module configuration - Server and communication settings."""

# ============================================================================
# SERVER - Configuration du serveur SSE (Server-Sent Events)
# ============================================================================

# Port du serveur SSE pour communication avec le visualiseur
# Note: Port changé de 5432 à 5433 (5432 souvent utilisé par PostgreSQL)
SSE_PORT = 5433

# Adresse IP du serveur SSE (127.0.0.1 = localhost uniquement)
SSE_HOST = "127.0.0.1"
