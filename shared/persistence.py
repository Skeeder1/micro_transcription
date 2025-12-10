"""
Persistent user settings stored in parametre.json.

Provides thread-safe load/save for runtime-changeable settings
that persist across application restarts.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import TypedDict, Optional

from shared.logger import log_info, log_warn


class UserSettings(TypedDict):
    """User-configurable settings that persist across sessions."""
    vad_bypass: bool


# Default values for all settings
DEFAULT_SETTINGS: UserSettings = {
    "vad_bypass": False,
}

# File location (project root)
SETTINGS_FILE = Path(__file__).parent.parent / "parametre.json"

# Thread-safe access
_settings_lock = threading.Lock()
_cached_settings: Optional[UserSettings] = None


def load_settings() -> UserSettings:
    """
    Load settings from JSON file.

    Creates the file with defaults if it doesn't exist.
    Uses in-memory cache to avoid repeated file reads.

    Returns:
        UserSettings dict with current values.
    """
    global _cached_settings

    with _settings_lock:
        if _cached_settings is not None:
            return _cached_settings.copy()

        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Merge with defaults (handles new settings added later)
                _cached_settings = {**DEFAULT_SETTINGS, **data}
                log_info(f"[Persistence] Loaded settings from {SETTINGS_FILE}")
            except (json.JSONDecodeError, IOError) as e:
                log_warn(f"[Persistence] Error loading {SETTINGS_FILE}: {e}")
                _cached_settings = DEFAULT_SETTINGS.copy()
        else:
            _cached_settings = DEFAULT_SETTINGS.copy()
            _save_settings_internal(_cached_settings)
            log_info(f"[Persistence] Created default settings at {SETTINGS_FILE}")

        return _cached_settings.copy()


def save_settings(settings: UserSettings) -> bool:
    """
    Save settings to JSON file.

    Args:
        settings: UserSettings dict to save.

    Returns:
        True if save succeeded, False otherwise.
    """
    global _cached_settings

    with _settings_lock:
        if _save_settings_internal(settings):
            _cached_settings = settings.copy()
            return True
        return False


def _save_settings_internal(settings: UserSettings) -> bool:
    """
    Internal save without lock (caller must hold lock).

    Args:
        settings: UserSettings dict to save.

    Returns:
        True if save succeeded, False otherwise.
    """
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        log_info(f"[Persistence] Saved settings to {SETTINGS_FILE}")
        return True
    except IOError as e:
        log_warn(f"[Persistence] Error saving {SETTINGS_FILE}: {e}")
        return False


def get_vad_bypass() -> bool:
    """
    Get current VAD bypass setting.

    Returns:
        True if VAD bypass is enabled, False otherwise.
    """
    return load_settings()["vad_bypass"]


def set_vad_bypass(enabled: bool) -> bool:
    """
    Set VAD bypass and persist to file.

    Args:
        enabled: True to enable VAD bypass, False to disable.

    Returns:
        True if save succeeded, False otherwise.
    """
    settings = load_settings()
    settings["vad_bypass"] = enabled
    return save_settings(settings)


def invalidate_cache() -> None:
    """
    Invalidate the settings cache.

    Forces next load_settings() to read from file.
    Useful for testing or external file modifications.
    """
    global _cached_settings
    with _settings_lock:
        _cached_settings = None
