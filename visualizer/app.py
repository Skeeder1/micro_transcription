"""Visualizer REST API server using Flask."""

from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path
from typing import Iterator

from flask import Flask, Response, jsonify, render_template, request
from flask_cors import CORS

# Add parent directory to import shared_state
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from shared_state import SharedState

from . import config
from .state_watcher import StateWatcher

# Flask app
app = Flask(__name__)
app.logger.disabled = not config.DEBUG

# Enable CORS if configured
if config.CORS_ENABLED:
    CORS(app, origins=config.CORS_ORIGINS)

# Shared state (file-based, synchronized with transcription app)
_shared_state = SharedState(source="visualizer")

# SSE clients queue
_sse_clients: list[queue.Queue[str | None]] = []
_sse_lock = threading.Lock()

# State watcher to broadcast changes
_state_watcher: StateWatcher | None = None


# ============================================================================
# SSE Endpoints (Server-Sent Events for real-time updates)
# ============================================================================


def _event_stream() -> Iterator[str]:
    """Generate SSE messages for connected clients."""
    messages: "queue.Queue[str | None]" = queue.Queue()

    with _sse_lock:
        _sse_clients.append(messages)
        count = len(_sse_clients)

    if config.DEBUG:
        print(f"[SSE] New client connected. Total: {count}")

    try:
        while True:
            msg = messages.get()
            if msg is None:
                break
            if config.DEBUG:
                print(f"[SSE] Sending message: '{msg[:50]}...'")
            yield f"data: {msg}\n\n"
    finally:
        with _sse_lock:
            _sse_clients.remove(messages)
            count = len(_sse_clients)
        if config.DEBUG:
            print(f"[SSE] Client disconnected. Remaining: {count}")


@app.route("/events")
def sse_endpoint() -> Response:
    """SSE endpoint for real-time updates to the visualizer UI."""
    response = Response(_event_stream(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


def _broadcast_to_clients(message: str) -> None:
    """Send message to all connected SSE clients."""
    with _sse_lock:
        if config.DEBUG and not _sse_clients:
            print(f"[SSE] No clients to receive: '{message[:50]}...'")
        elif config.DEBUG:
            print(f"[SSE] Broadcasting to {len(_sse_clients)} client(s): '{message[:50]}...'")

        for client in _sse_clients:
            try:
                client.put_nowait(message)
            except queue.Full:
                pass


# ============================================================================
# REST API Endpoints
# ============================================================================


@app.route(f"{config.API_PREFIX}/preview", methods=["POST"])
def api_preview() -> tuple[dict, int]:
    """Update preview text.

    Body:
        {
            "text": "Preview text to display"
        }
    """
    data = request.get_json()
    if not data or "text" not in data:
        return {"error": "Missing 'text' field"}, 400

    text = data["text"]

    # Update state
    with _state_lock:
        _state["preview_text"] = text

    # Broadcast to clients
    _broadcast_to_clients(text)

    return {"status": "ok", "text": text}, 200


@app.route(f"{config.API_PREFIX}/state", methods=["POST"])
def api_state() -> tuple[dict, int]:
    """Update visualizer state.

    Body:
        {
            "state": "active" | "sleep"
        }
    """
    data = request.get_json()
    if not data or "state" not in data:
        return {"error": "Missing 'state' field"}, 400

    state = data["state"]
    if state not in ["active", "sleep"]:
        return {"error": "Invalid state. Must be 'active' or 'sleep'"}, 400

    # Update state
    with _state_lock:
        _state["status"] = state

    # Broadcast state change to clients
    message = f"STATE:{state}"
    _broadcast_to_clients(message)

    return {"status": "ok", "state": state}, 200


@app.route(f"{config.API_PREFIX}/status", methods=["GET"])
def api_status() -> tuple[dict, int]:
    """Get current visualizer status."""
    # Read from shared state file
    status = {
        "status": "sleep" if _shared_state.get_sleep_state() else "active",
        "preview_text": _shared_state.get_preview_text(),
        "connected_clients": 0,
        "last_update": _shared_state.get_last_update_time(),
        "source": _shared_state.get_state_source()
    }

    with _sse_lock:
        status["connected_clients"] = len(_sse_clients)

    return status, 200


@app.route(f"{config.API_PREFIX}/clear", methods=["POST"])
def api_clear() -> tuple[dict, int]:
    """Clear preview text."""
    with _state_lock:
        _state["preview_text"] = ""

    _broadcast_to_clients("")

    return {"status": "ok"}, 200


# ============================================================================
# Web UI Endpoints
# ============================================================================


@app.route("/")
def index() -> str:
    """Serve the visualizer web interface."""
    return render_template("index.html", sse_port=config.SSE_PORT)


@app.route("/ping")
def ping() -> str:
    """Healthcheck endpoint."""
    return "pong"


# ============================================================================
# Programmatic API (for embedding in other apps)
# ============================================================================


def broadcast_preview(text: str) -> None:
    """Programmatically broadcast preview text to all clients."""
    with _state_lock:
        _state["preview_text"] = text
    _broadcast_to_clients(text)


def broadcast_state(state: str) -> None:
    """Programmatically broadcast state change to all clients."""
    if state not in ["active", "sleep"]:
        raise ValueError(f"Invalid state: {state}")

    with _state_lock:
        _state["status"] = state

    message = f"STATE:{state}"
    _broadcast_to_clients(message)


def get_status() -> dict:
    """Programmatically get current status."""
    with _state_lock:
        state_copy = _state.copy()

    with _sse_lock:
        state_copy["connected_clients"] = len(_sse_clients)

    return state_copy
