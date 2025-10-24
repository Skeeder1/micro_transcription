"""Transcription API routes - SSE endpoints for real-time transcription."""

from __future__ import annotations

from flask import Blueprint, Response

from api.server import event_stream, _CTX


bp = Blueprint('transcription', __name__)


@bp.route("/events")
def sse_endpoint() -> Response:
    """Expose the SSE stream for the visualizer."""
    if _CTX is None:
        raise RuntimeError("SSE context not initialised")
    response = Response(event_stream(_CTX), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


@bp.route("/ping")
def ping() -> str:
    """Healthcheck endpoint."""
    return "pong"
