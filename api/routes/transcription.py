"""Transcription API routes - SSE endpoints for real-time transcription."""

from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from api.server import event_stream, _CTX
from shared.persistence import get_vad_bypass, set_vad_bypass
from shared.logger import log_info


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
            "is_sleeping": True,
            "vad_bypass": False
        })

    with _CTX.recording_lock:
        is_recording = _CTX.is_recording

    with _CTX.sleep_lock:
        is_sleeping = _CTX.is_sleeping

    with _CTX.vad_bypass_lock:
        vad_bypass = _CTX.vad_bypass

    response = jsonify({
        "is_recording": is_recording,
        "is_sleeping": is_sleeping,
        "vad_bypass": vad_bypass
    })
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@bp.route("/settings/vad-bypass", methods=["GET"])
def get_vad_bypass_endpoint() -> Response:
    """Get current VAD bypass setting."""
    if _CTX is None:
        return jsonify({"vad_bypass": False})

    with _CTX.vad_bypass_lock:
        current = _CTX.vad_bypass

    response = jsonify({"vad_bypass": current})
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@bp.route("/settings/vad-bypass", methods=["POST"])
def set_vad_bypass_endpoint() -> Response:
    """Set VAD bypass setting (persists to parametre.json)."""
    if _CTX is None:
        response = jsonify({"error": "Context not initialized"})
        response.status_code = 500
        return response

    data = request.get_json()
    if data is None or "vad_bypass" not in data:
        response = jsonify({"error": "Missing vad_bypass field"})
        response.status_code = 400
        return response

    enabled = bool(data["vad_bypass"])

    # Update runtime state
    with _CTX.vad_bypass_lock:
        _CTX.vad_bypass = enabled

    # Persist to file
    success = set_vad_bypass(enabled)

    log_info(f"[API] VAD bypass {'enabled' if enabled else 'disabled'}")

    response = jsonify({
        "vad_bypass": enabled,
        "persisted": success
    })
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@bp.route("/settings/vad-bypass", methods=["OPTIONS"])
def vad_bypass_options() -> Response:
    """Handle CORS preflight for vad-bypass endpoint."""
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response
