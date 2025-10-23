"""Adapter for backward compatibility with the old SSE-based system.

This module provides a compatibility layer that allows existing code
using the old SSE broadcast functions to work with the new REST API client.
"""

from __future__ import annotations

from typing import Optional

from . import config
from .client import VisualizerClient

# Global client instance
_client: Optional[VisualizerClient] = None


def get_or_create_client() -> VisualizerClient:
    """Get or create the global client instance."""
    global _client
    if _client is None:
        _client = VisualizerClient(host=config.HOST, port=config.PORT)
    return _client


# ============================================================================
# Backward-compatible API (mimics old SSE module interface)
# ============================================================================


def broadcast_preview(text: str) -> None:
    """Send preview text to the visualizer (backward compatible).

    This function mimics the old SSE broadcast_preview function.
    Fails silently if visualizer is not available.
    """
    try:
        client = get_or_create_client()
        client.send_preview(text)
    except Exception:
        # Silent failure - visualizer not available
        pass


def broadcast_state(state: str) -> None:
    """Send state change to the visualizer (backward compatible).

    This function mimics the old SSE broadcast_state function.
    Fails silently if visualizer is not available.
    """
    try:
        client = get_or_create_client()
        client.set_state(state)
    except Exception:
        # Silent failure - visualizer not available
        pass


def is_visualizer_available() -> bool:
    """Check if the visualizer server is available."""
    client = get_or_create_client()
    return client.ping()


# ============================================================================
# Migration helper
# ============================================================================


def create_migration_guide() -> str:
    """Return a migration guide for updating existing code."""
    return """
    Migration Guide: Old SSE System → New REST API
    ================================================

    The visualizer now uses a REST API instead of SSE broadcasts.

    Old Code (SSE):
    ----------------
    from transcription_app.sse import broadcast_preview, broadcast_state

    broadcast_preview(ctx, "Hello world")
    broadcast_state(ctx, "sleep")

    New Code (REST API - Option 1: Direct client):
    -----------------------------------------------
    from visualizer.client import VisualizerClient

    client = VisualizerClient()
    client.send_preview("Hello world")
    client.set_state("sleep")

    New Code (REST API - Option 2: Convenience):
    ---------------------------------------------
    from visualizer import client

    client.send_preview("Hello world")
    client.set_state("sleep")

    New Code (Adapter - easiest migration):
    ----------------------------------------
    from visualizer.adapter import broadcast_preview, broadcast_state

    broadcast_preview("Hello world")  # No ctx needed!
    broadcast_state("sleep")

    Benefits of the new system:
    ----------------------------
    ✓ No need to pass AppContext (ctx) around
    ✓ Visualizer runs as independent service
    ✓ Can be queried via REST API from any language
    ✓ Can run on different machine
    ✓ Easier to test and debug
    ✓ Better error handling
    """


if __name__ == "__main__":
    print(create_migration_guide())
