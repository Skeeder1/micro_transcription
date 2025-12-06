"""Transcription API routes - SSE endpoints for real-time transcription."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify

from api.server import event_stream, _CTX


bp = Blueprint('transcription', __name__)


@bp.route("/events")
def sse_endpoint() -> Response:
    """Expose the SSE stream for the visualizer."""
    if _CTX is None:
        raise RuntimeError("SSE context not initialised")
    response = Response(event_stream(_CTX), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@bp.route("/ping")
def ping() -> str:
    """Healthcheck endpoint."""
    return "pong"


@bp.route("/status")
def status() -> Response:
    """Get current system status for initial UI sync."""
    if _CTX is None:
        return jsonify({
            "is_recording": False,
            "is_sleeping": True
        })

    with _CTX.recording_lock:
        is_recording = _CTX.is_recording

    with _CTX.sleep_lock:
        is_sleeping = _CTX.is_sleeping

    response = jsonify({
        "is_recording": is_recording,
        "is_sleeping": is_sleeping
    })
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response
