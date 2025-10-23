"""State manager for transcription app using shared state."""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path to import shared_state
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from shared_state import SharedState


class TranscriptionStateManager:
    """Manages state for the transcription app using shared state file."""

    def __init__(self):
        """Initialize state manager."""
        self.state = SharedState(source="transcription")

    def update_sleep_state(self, is_sleeping: bool):
        """Update sleep state in shared state."""
        self.state.set_sleep_state(is_sleeping)

    def update_preview(self, text: str):
        """Update preview text in shared state."""
        self.state.set_preview_text(text)

    def is_sleeping(self) -> bool:
        """Get current sleep state."""
        return self.state.get_sleep_state()


# Global instance
_state_manager: TranscriptionStateManager | None = None


def get_state_manager() -> TranscriptionStateManager:
    """Get or create global state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = TranscriptionStateManager()
    return _state_manager
