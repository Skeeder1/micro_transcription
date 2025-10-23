"""Visualizer configuration."""

# Server configuration
HOST = "127.0.0.1"
PORT = 5500

# API configuration
API_PREFIX = "/api"

# SSE configuration - for backward compatibility
SSE_PORT = PORT
SSE_HOST = HOST

# Debug mode
DEBUG = False

# CORS settings - allow requests from anywhere
CORS_ENABLED = True
CORS_ORIGINS = "*"
