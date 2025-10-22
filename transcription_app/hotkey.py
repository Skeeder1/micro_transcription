"""Hotkey management using pynput.

Changed: F9 now toggles the dictaphone (replaces previous AltGr + ; mapping).
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

from pynput import keyboard as pynput_keyboard


class HotkeyManager:
    """Listens for the F9 key to toggle the dictaphone.

    The previous implementation used AltGr + ; (with tolerant sequencing).
    For simplicity and reliability we now trigger the toggle immediately on
    an F9 press. The old Alt/AltGr/semicolon state tracking is kept but
    is no longer required for the primary F9 behaviour.
    """

    def __init__(self, on_toggle: Callable[[], None]) -> None:
        self._on_toggle = on_toggle
        self._listener: Optional[pynput_keyboard.Listener] = None
        self._lock = threading.Lock()

        # Only F9 is used as the toggle hotkey now. Keep minimal state.
        self._state = {"consumed": False}

    def start(self) -> None:
        if self._listener is not None:
            return
        self._listener = pynput_keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
            suppress=False,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener is None:
            return
        self._listener.stop()
        try:
            self._listener.join(timeout=0.5)
        except RuntimeError:
            pass
        finally:
            self._listener = None

    def _is_semicolon(
        self, key: Optional[pynput_keyboard.Key | pynput_keyboard.KeyCode]
    ) -> bool:
        # Semicolon detection removed; keep method for compatibility but
        # always return False.
        return False

    def _handle_press(
        self, key: Optional[pynput_keyboard.Key | pynput_keyboard.KeyCode]
    ) -> None:
        triggered = False

        with self._lock:
            try:
                if key is None:
                    return
                # Immediate toggle on F9 key
                if key == pynput_keyboard.Key.f9 and not self._state.get("consumed", False):
                    self._state["consumed"] = True
                    triggered = True

            except AttributeError:
                pass

        if triggered:
            threading.Thread(target=self._on_toggle, name="HotkeyToggle", daemon=True).start()

    def _handle_release(
        self, key: Optional[pynput_keyboard.Key | pynput_keyboard.KeyCode]
    ) -> None:
        with self._lock:
            try:
                if key is None:
                    return
                # If F9 released, allow subsequent presses to trigger again
                if key == pynput_keyboard.Key.f9:
                    self._state["consumed"] = False

            except AttributeError:
                pass
