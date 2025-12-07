"""Service registry utilities for dependency injection.

This module provides convenient accessor functions for commonly used services
registered in the ServiceRegistry, reducing code duplication across modules.

Usage:
    from shared.service_utils import get_broadcaster, broadcast_preview_safe

    # Get broadcaster (returns None if not registered)
    broadcaster = get_broadcaster()
    if broadcaster:
        broadcaster.send_preview(ctx, "Hello")

    # Broadcast preview safely (never raises)
    broadcast_preview_safe(ctx, "Hello world")
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from shared.interfaces import IBroadcaster, ServiceRegistry

if TYPE_CHECKING:
    from shared.context import AppContext


# =============================================================================
# Service Accessors
# =============================================================================

def get_broadcaster() -> Optional[IBroadcaster]:
    """
    Get the broadcaster service from ServiceRegistry.

    Returns:
        IBroadcaster implementation or None if not registered.
    """
    return ServiceRegistry.get(IBroadcaster)


# =============================================================================
# Safe Broadcast Utilities
# =============================================================================

def broadcast_preview_safe(ctx: "AppContext", text: str) -> bool:
    """
    Broadcast preview text safely.

    Args:
        ctx: Application context
        text: Preview text to broadcast

    Returns:
        True if broadcast succeeded, False if broadcaster unavailable
    """
    broadcaster = get_broadcaster()
    if broadcaster:
        broadcaster.send_preview(ctx, text)
        return True
    return False


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "get_broadcaster",
    "broadcast_preview_safe",
]
