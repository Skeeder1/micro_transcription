"""Background watcher for shared state changes.

This module watches the shared state file and broadcasts changes to SSE clients.
"""

import sys
import threading
import time
from pathlib import Path

# Add parent directory to import shared_state
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from shared_state import SharedState


class StateWatcher:
    """Watches shared state and triggers callbacks on changes."""

    def __init__(self, on_state_change: callable = None, on_preview_change: callable = None):
        """Initialize state watcher.

        Args:
            on_state_change: Callback(is_sleeping: bool) when sleep state changes
            on_preview_change: Callback(text: str) when preview text changes
        """
        self.shared_state = SharedState(source="visualizer_watcher")
        self.on_state_change = on_state_change
        self.on_preview_change = on_preview_change

        self.last_sleep_state = None
        self.last_preview_text = None
        self.running = False
        self.thread = None

    def start(self):
        """Start watching for state changes."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._watch_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop watching."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _watch_loop(self):
        """Main watching loop."""
        while self.running:
            try:
                # Check sleep state
                current_sleep_state = self.shared_state.get_sleep_state()
                if current_sleep_state != self.last_sleep_state:
                    self.last_sleep_state = current_sleep_state
                    if self.on_state_change:
                        self.on_state_change(current_sleep_state)

                # Check preview text
                current_preview = self.shared_state.get_preview_text()
                if current_preview != self.last_preview_text:
                    self.last_preview_text = current_preview
                    if self.on_preview_change:
                        self.on_preview_change(current_preview)

            except Exception as e:
                print(f"[StateWatcher] Error: {e}")

            # Poll every 100ms
            time.sleep(0.1)
