"""Shared state management for synchronizing transcription and visualizer.

This module provides a simple file-based state management system that allows
the transcription app and visualizer to communicate without direct coupling.

State File Format (JSON):
{
    "is_sleeping": false,
    "last_update": 1234567890.123,
    "preview_text": "Current transcription...",
    "source": "transcription"  // or "visualizer"
}
"""

import json
import time
from pathlib import Path
from typing import Any, Optional


# State file location
STATE_FILE = Path(__file__).parent / ".app_state.json"
STATE_LOCK_FILE = Path(__file__).parent / ".app_state.lock"


class SharedState:
    """Shared state manager using file-based storage."""

    def __init__(self, source: str = "unknown"):
        """Initialize shared state manager.

        Args:
            source: Identifier for this instance (e.g., "transcription", "visualizer")
        """
        self.source = source
        self._ensure_state_file()

    def _ensure_state_file(self):
        """Ensure state file exists with default values."""
        if not STATE_FILE.exists():
            self._write_state({
                "is_sleeping": False,
                "last_update": time.time(),
                "preview_text": "",
                "source": self.source
            })

    def _read_state(self) -> dict[str, Any]:
        """Read current state from file."""
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default state if file is missing or corrupted
            return {
                "is_sleeping": False,
                "last_update": 0,
                "preview_text": "",
                "source": "unknown"
            }

    def _write_state(self, state: dict[str, Any]):
        """Write state to file."""
        try:
            # Add timestamp and source
            state["last_update"] = time.time()
            state["source"] = self.source

            # Write to temp file first, then rename (atomic on most systems)
            temp_file = STATE_FILE.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)

            # Atomic rename
            temp_file.replace(STATE_FILE)
        except Exception as e:
            print(f"[SharedState] Error writing state: {e}")

    def get_sleep_state(self) -> bool:
        """Get current sleep state.

        Returns:
            True if system is sleeping, False otherwise
        """
        state = self._read_state()
        return state.get("is_sleeping", False)

    def set_sleep_state(self, is_sleeping: bool):
        """Set sleep state.

        Args:
            is_sleeping: True to sleep, False to wake
        """
        state = self._read_state()
        state["is_sleeping"] = is_sleeping
        self._write_state(state)

    def get_preview_text(self) -> str:
        """Get current preview text.

        Returns:
            Current preview text
        """
        state = self._read_state()
        return state.get("preview_text", "")

    def set_preview_text(self, text: str):
        """Set preview text.

        Args:
            text: Preview text to set
        """
        state = self._read_state()
        state["preview_text"] = text
        self._write_state(state)

    def get_last_update_time(self) -> float:
        """Get timestamp of last state update.

        Returns:
            Unix timestamp of last update
        """
        state = self._read_state()
        return state.get("last_update", 0)

    def get_state_source(self) -> str:
        """Get the source of the last state update.

        Returns:
            Source identifier ("transcription", "visualizer", etc.)
        """
        state = self._read_state()
        return state.get("source", "unknown")

    def get_state(self) -> dict[str, Any]:
        """Get complete current state.

        Returns:
            Dictionary containing all state data
        """
        return self._read_state()

    def wait_for_state_change(self, timeout: float = 1.0) -> bool:
        """Wait for state to change (polling-based).

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if state changed, False if timeout
        """
        initial_time = self.get_last_update_time()
        start = time.time()

        while time.time() - start < timeout:
            current_time = self.get_last_update_time()
            if current_time > initial_time:
                return True
            time.sleep(0.1)

        return False

    def clear(self):
        """Clear/reset state to defaults."""
        self._write_state({
            "is_sleeping": False,
            "last_update": time.time(),
            "preview_text": "",
            "source": self.source
        })


# Convenience functions for backward compatibility
_default_state: Optional[SharedState] = None


def get_shared_state(source: str = "unknown") -> SharedState:
    """Get or create default shared state instance."""
    global _default_state
    if _default_state is None:
        _default_state = SharedState(source)
    return _default_state


def get_sleep_state() -> bool:
    """Get current sleep state (convenience function)."""
    return get_shared_state().get_sleep_state()


def set_sleep_state(is_sleeping: bool):
    """Set sleep state (convenience function)."""
    get_shared_state().set_sleep_state(is_sleeping)


if __name__ == "__main__":
    # Test the shared state system
    print("Testing shared state system...")

    state = SharedState("test")

    # Test sleep state
    print(f"Initial sleep state: {state.get_sleep_state()}")
    state.set_sleep_state(True)
    print(f"After setting to sleep: {state.get_sleep_state()}")
    state.set_sleep_state(False)
    print(f"After waking: {state.get_sleep_state()}")

    # Test preview text
    state.set_preview_text("Hello world")
    print(f"Preview text: {state.get_preview_text()}")

    # Test source tracking
    print(f"Last update source: {state.get_state_source()}")

    print("\n✅ Shared state system working!")
