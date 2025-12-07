"""API Server - Flask server for inter-module communication via SSE.

This module provides the SSE broadcast infrastructure and implements
the IBroadcaster interface for decoupled module communication.

Usage:
    # Direct function calls (legacy)
    from api.server import broadcast_preview
    broadcast_preview(ctx, "Hello")

    # Via ServiceRegistry (recommended for new code)
    from shared.interfaces import ServiceRegistry, IBroadcaster
    broadcaster = ServiceRegistry.get(IBroadcaster)
    broadcaster.send_preview(ctx, "Hello")

Phase 4 Integration:
- Uses ServiceRegistry to register IBroadcaster implementation
- Error handling for server operations
"""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING, Iterator, Optional

from flask import Flask

from shared import config
from shared.constants import LOG_PREFIX_SSE, SSE_BROADCAST_TIMEOUT
from shared.context import AppContext
from shared.interfaces import IBroadcaster, ServiceRegistry
from shared.logger import log_info, log_warn, log_error
from shared.errors import handle_errors
from shared.threading_utils import TimeoutLock

if TYPE_CHECKING:
    pass


app = Flask(__name__)
app.logger.disabled = True

_CTX: Optional[AppContext] = None

# Module-level TimeoutLock for SSE broadcast operations
# Prevents deadlocks in SSE broadcast operations
_sse_broadcast_lock = TimeoutLock(timeout=SSE_BROADCAST_TIMEOUT, name="sse_broadcast")


# =============================================================================
# SSE Broadcaster Implementation
# =============================================================================

class SSEBroadcaster:
    """
    Implementation of IBroadcaster using Server-Sent Events.

    This class provides a clean interface for broadcasting messages
    to connected SSE clients while implementing the IBroadcaster protocol.
    """

    def send_preview(self, ctx: AppContext, text: str) -> None:
        """Send preview text to all connected clients."""
        broadcast_preview(ctx, text)

    def send_state(self, ctx: AppContext, state: str) -> None:
        """Send state change to all connected clients."""
        broadcast_state(ctx, state)

    def send_vad(self, ctx: AppContext, is_voice: bool) -> None:
        """Send VAD state to all connected clients."""
        broadcast_vad(ctx, is_voice)

    def send_processing(self, ctx: AppContext, is_processing: bool) -> None:
        """Send processing state to all connected clients."""
        broadcast_processing(ctx, is_processing)

    def send_recording(self, ctx: AppContext, is_recording: bool) -> None:
        """Send recording state to all connected clients."""
        broadcast_recording(ctx, is_recording)


# Singleton broadcaster instance
_broadcaster: Optional[SSEBroadcaster] = None


def get_broadcaster() -> SSEBroadcaster:
    """Get or create the broadcaster singleton."""
    global _broadcaster
    if _broadcaster is None:
        _broadcaster = SSEBroadcaster()
        ServiceRegistry.register(IBroadcaster, _broadcaster)
    return _broadcaster


# =============================================================================
# SSE Event Stream
# =============================================================================


def _safe_broadcast(ctx: AppContext, message: str, log_message: Optional[str] = None) -> bool:
    """
    Safely broadcast a message to all SSE clients with timeout protection.

    Uses TimeoutLock to prevent deadlocks in concurrent broadcast scenarios.

    Args:
        ctx: Application context
        message: Message to broadcast
        log_message: Optional log message (defaults to message preview)

    Returns:
        True if broadcast succeeded, False if lock acquisition timed out
    """
    try:
        with _sse_broadcast_lock:
            # Use the original context lock for client list access
            with ctx.sse_lock:
                if log_message:
                    if ctx.sse_clients:
                        log_info(f"{LOG_PREFIX_SSE} {log_message}")
                    else:
                        log_info(f"{LOG_PREFIX_SSE} Aucun client pour: {log_message}")

                for client in ctx.sse_clients:
                    try:
                        client.put_nowait(message)
                    except queue.Full:
                        pass
            return True
    except TimeoutError:
        log_warn(f"{LOG_PREFIX_SSE} Broadcast timeout - message perdu: '{message[:30]}...'")
        return False


def event_stream(ctx: AppContext) -> Iterator[str]:
    """Generate SSE messages for connected clients."""
    messages: "queue.Queue[str | None]" = queue.Queue()
    with ctx.sse_lock:
        ctx.sse_clients.append(messages)
        log_info(f"{LOG_PREFIX_SSE} Nouveau client connecté. Total: {len(ctx.sse_clients)}")

    try:
        while True:
            msg = messages.get()
            if msg is None:
                break
            log_info(f"{LOG_PREFIX_SSE} Envoi message: '{msg[:50]}...'")
            yield f"data: {msg}\n\n"
    finally:
        with ctx.sse_lock:
            ctx.sse_clients.remove(messages)
            log_info(f"{LOG_PREFIX_SSE} Client déconnecté. Restant: {len(ctx.sse_clients)}")


def broadcast_preview(ctx: AppContext, text: str) -> None:
    """Send preview text to all connected SSE clients."""
    preview = text[:50] + "..." if len(text) > 50 else text
    _safe_broadcast(ctx, text, log_message=f"Envoi preview: '{preview}'")


def broadcast_state(ctx: AppContext, state: str) -> None:
    """Send state change to all connected SSE clients."""
    message = f"STATE:{state}"
    _safe_broadcast(ctx, message, log_message=f"Envoi état: '{state}'")


def broadcast_recording(ctx: AppContext, is_recording: bool) -> None:
    """Send recording state change to all connected SSE clients."""
    state = "recording" if is_recording else "paused"
    message = f"RECORDING:{state}"
    _safe_broadcast(ctx, message)


def broadcast_vad(ctx: AppContext, is_voice: bool) -> None:
    """
    Send VAD (Voice Activity Detection) state to all connected SSE clients.

    This is used by the frontend to show the VAD indicator:
    - Green when voice is detected
    - Gray during silence

    Args:
        ctx: Application context
        is_voice: True if voice is currently being detected
    """
    state = "active" if is_voice else "inactive"
    message = f"VAD:{state}"
    _safe_broadcast(ctx, message)


def broadcast_processing(ctx: AppContext, is_processing: bool) -> None:
    """
    Send processing state to all connected SSE clients.

    This is used by the frontend to show the AI processing indicator
    when transcription is in progress.

    Args:
        ctx: Application context
        is_processing: True if transcription is in progress
    """
    state = "start" if is_processing else "done"
    message = f"PROCESSING:{state}"
    _safe_broadcast(ctx, message)


def init_routes(ctx: AppContext) -> None:
    """Initialize all API routes and register services."""
    global _CTX
    _CTX = ctx

    # Initialize and register the broadcaster
    get_broadcaster()

    # Import routes here to avoid circular imports
    from api.routes import transcription

    # Register blueprints
    app.register_blueprint(transcription.bp)


@handle_errors(log_prefix=LOG_PREFIX_SSE, reraise=True)
def start_server(ctx: AppContext) -> None:
    """Start the SSE server on a background thread."""
    init_routes(ctx)

    def run() -> None:
        try:
            from werkzeug.serving import make_server

            server = make_server(config.SSE_HOST, config.SSE_PORT, app, threaded=True)
            log_info(f"Serveur API démarré sur http://{config.SSE_HOST}:{config.SSE_PORT}")
            server.serve_forever()
        except Exception as exc:
            log_error(f"{LOG_PREFIX_SSE} Erreur serveur: {exc}")

    thread = threading.Thread(target=run, daemon=True, name="SSEServer")
    thread.start()
