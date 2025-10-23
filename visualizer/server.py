"""Standalone visualizer server launcher."""

from __future__ import annotations

import sys
import threading
from typing import Optional

from werkzeug.serving import make_server

from . import config
from .app import app


def run_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    debug: Optional[bool] = None,
    threaded: bool = True,
) -> None:
    """Run the visualizer server.

    Args:
        host: Host address (default: from config)
        port: Port number (default: from config)
        debug: Debug mode (default: from config)
        threaded: Enable threading (default: True)
    """
    host = host or config.HOST
    port = port or config.PORT
    debug = debug if debug is not None else config.DEBUG

    print(f"🎵 Visualiseur Audio (Module Indépendant)")
    print(f"=" * 50)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"")
    print(f"🌐 Interface web: http://{host}:{port}")
    print(f"📡 API REST: http://{host}:{port}{config.API_PREFIX}")
    print(f"🔄 SSE Stream: http://{host}:{port}/events")
    print(f"")
    print(f"ℹ️  Ce module est synchronisé automatiquement avec")
    print(f"   l'application de transcription via fichier d'état")
    print(f"")
    print(f"Press Ctrl+C to stop")
    print("")

    # Start state watcher to monitor shared state file
    from .state_watcher import StateWatcher
    from . import app as app_module

    def on_state_change(is_sleeping: bool):
        """Called when sleep state changes."""
        state_msg = "sleep" if is_sleeping else "active"
        message = f"STATE:{state_msg}"
        with app_module._sse_lock:
            for client in app_module._sse_clients:
                try:
                    client.put_nowait(message)
                except queue.Full:
                    pass

    def on_preview_change(text: str):
        """Called when preview text changes."""
        with app_module._sse_lock:
            for client in app_module._sse_clients:
                try:
                    client.put_nowait(text)
                except queue.Full:
                    pass

    watcher = StateWatcher(
        on_state_change=on_state_change,
        on_preview_change=on_preview_change
    )
    watcher.start()
    print("✅ État partagé: Surveillance active")
    print("")

    server = make_server(host, port, app, threaded=threaded)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down server...")
        watcher.stop()
        server.shutdown()


def run_server_background(
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> threading.Thread:
    """Run the visualizer server in a background thread.

    Args:
        host: Host address (default: from config)
        port: Port number (default: from config)

    Returns:
        The server thread
    """
    host = host or config.HOST
    port = port or config.PORT

    def _run():
        server = make_server(host, port, app, threaded=True)
        print(f"🎵 Visualizer Server running at http://{host}:{port}")
        server.serve_forever()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread


def main() -> None:
    """Main entry point for the standalone server."""
    # Parse command line arguments
    host = config.HOST
    port = config.PORT
    debug = config.DEBUG

    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Error: Invalid port number '{sys.argv[1]}'")
            sys.exit(1)

    if len(sys.argv) > 2:
        host = sys.argv[2]

    run_server(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
