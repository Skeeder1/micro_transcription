"""Compat entry point delegating to the modular transcription package."""

from __future__ import annotations

import sys

from transcription_app.app import run


def main() -> int:
    """Entry point kept for backward compatibility with legacy scripts."""

    return run()


if __name__ == "__main__":
    sys.exit(main())
