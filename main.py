"""Main entry point for the modular transcription application.

This is the new unified entry point that orchestrates all modules:
- core: Transcription engine
- ui: Visualizer interface
- api: REST API server for inter-module communication
- shared: Common utilities (hotkey, sleep, config)
- services: Future AutoGen integration (stub)

Architecture:
    main.py → core.engine → [ui, api, shared]
"""

from __future__ import annotations

import sys

from core.engine import run


def main() -> int:
    """Main entry point for the application."""
    return run()


if __name__ == "__main__":
    sys.exit(main())
