"""API Server - Flask server for inter-module communication via SSE."""

from __future__ import annotations

import queue
import threading
from typing import Iterator, Optional

from flask import Flask

from shared import config
from shared.context import AppContext


app = Flask(__name__)
app.logger.disabled = True

_CTX: Optional[AppContext] = None


def event_stream(ctx: AppContext) -> Iterator[str]:
    """Generate SSE messages for connected clients."""
    messages: "queue.Queue[str | None]" = queue.Queue()
    with ctx.sse_lock:
        ctx.sse_clients.append(messages)
        print(f"[SSE] Nouveau client connecté. Total: {len(ctx.sse_clients)}")

    try:
        while True:
            msg = messages.get()
            if msg is None:
                break
            print(f"[SSE] Envoi message: '{msg[:50]}...'")
            yield f"data: {msg}\n\n"
    finally:
        with ctx.sse_lock:
            ctx.sse_clients.remove(messages)
            print(f"[SSE] Client déconnecté. Restant: {len(ctx.sse_clients)}")


def broadcast_preview(ctx: AppContext, text: str) -> None:
    """Send preview text to all connected SSE clients."""
    with ctx.sse_lock:
        if not ctx.sse_clients:
            print(f"\n[SSE] Aucun client pour recevoir: '{text[:50]}...'")
        else:
            print(f"\n[SSE] Envoi à {len(ctx.sse_clients)} client(s): '{text[:50]}...'")
        for client in ctx.sse_clients:
            try:
                client.put_nowait(text)
            except queue.Full:
                pass


def broadcast_state(ctx: AppContext, state: str) -> None:
    """Send state change to all connected SSE clients."""
    message = f"STATE:{state}"
    with ctx.sse_lock:
        if not ctx.sse_clients:
            print(f"\n[SSE] Aucun client pour recevoir l'état: '{state}'")
        else:
            print(f"\n[SSE] Envoi état à {len(ctx.sse_clients)} client(s): '{state}'")
        for client in ctx.sse_clients:
            try:
                client.put_nowait(message)
            except queue.Full:
                pass


def init_routes(ctx: AppContext) -> None:
    """Initialize all API routes."""
    global _CTX
    _CTX = ctx

    # Import routes here to avoid circular imports
    from api.routes import transcription

    # Register blueprints
    app.register_blueprint(transcription.bp)


def start_server(ctx: AppContext) -> None:
    """Start the SSE server on a background thread."""
    init_routes(ctx)

    def run() -> None:
        from werkzeug.serving import make_server

        server = make_server(config.SSE_HOST, config.SSE_PORT, app, threaded=True)
        print(f"🌐 Serveur API démarré sur http://{config.SSE_HOST}:{config.SSE_PORT}")
        server.serve_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
