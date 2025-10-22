"""Server-Sent Events helpers."""

from __future__ import annotations

import queue
import threading
from typing import Iterator, Optional

from flask import Flask, Response

from . import config
from .context import AppContext


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


@app.route("/events")
def sse_endpoint() -> Response:
    """Expose the SSE stream for the visualizer."""
    if _CTX is None:
        raise RuntimeError("SSE context not initialised")
    response = Response(event_stream(_CTX), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@app.route("/ping")
def ping() -> str:
    """Healthcheck endpoint."""
    return "pong"


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


def start_server(ctx: AppContext) -> None:
    """Start the SSE server on a background thread."""
    global _CTX
    _CTX = ctx
    def run() -> None:
        from werkzeug.serving import make_server

        server = make_server(config.SSE_HOST, config.SSE_PORT, app, threaded=True)
        print(f"🌐 Serveur SSE démarré sur http://{config.SSE_HOST}:{config.SSE_PORT}")
        server.serve_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
