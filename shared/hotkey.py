"""Hotkey management using pynput."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from pynput import keyboard as pynput_keyboard


class HotkeyManager:
    """Listens for the F9 key to toggle the dictaphone."""

    def __init__(self, on_toggle: Callable[[], None]) -> None:
        self._on_toggle = on_toggle
        self._listener: Optional[pynput_keyboard.Listener] = None
        self._lock = threading.Lock()
        self._state = {"consumed": False}
        self._last_press_time = 0.0

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

    def _handle_press(
        self, key: Optional[pynput_keyboard.Key | pynput_keyboard.KeyCode]
    ) -> None:
        triggered = False

        with self._lock:
            try:
                if key is None:
                    return
                # Immediate toggle on F9 key
                if key == pynput_keyboard.Key.f9:
                    # Protection: si consumed depuis > 2s, forcer reset
                    if self._state.get("consumed", False):
                        time_stuck = time.time() - self._last_press_time
                        if time_stuck > 2.0:
                            print(f"[Hotkey] WARN: consumed flag stuck for {time_stuck:.1f}s, forcing reset")
                            self._state["consumed"] = False

                    if not self._state.get("consumed", False):
                        self._state["consumed"] = True
                        self._last_press_time = time.time()
                        triggered = True

            except AttributeError:
                pass
            except Exception as exc:
                # NOUVEAU: Logger toute exception
                print(f"[Hotkey] ERROR in press handler: {exc}")
                self._state["consumed"] = False  # Reset en cas d'erreur

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
            except Exception as exc:
                # NOUVEAU: Logger et forcer reset
                print(f"[Hotkey] ERROR in release handler: {exc}")
                self._state["consumed"] = False
