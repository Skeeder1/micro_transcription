"""AltGr hotkey management using pynput."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from pynput import keyboard as pynput_keyboard

from . import config


class HotkeyManager:
    """Listens for the AltGr + ; hotkey (sequential tolerant)."""

    def __init__(self, on_toggle: Callable[[], None]) -> None:
        self._on_toggle = on_toggle
        self._listener: Optional[pynput_keyboard.Listener] = None
        self._lock = threading.Lock()

        self._state = {
            "alt": False,
            "ctrl": False,
            "altgr": False,
            "semicolon": False,
            "consumed": False,
        }
        self._last_press = {
            "alt": 0.0,
            "ctrl": 0.0,
            "altgr": 0.0,
            "semicolon": 0.0,
        }

        self._alt_keys = {
            pynput_keyboard.Key.alt,
            pynput_keyboard.Key.alt_l,
            pynput_keyboard.Key.alt_r,
        }
        self._ctrl_keys = {
            pynput_keyboard.Key.ctrl,
            pynput_keyboard.Key.ctrl_l,
            pynput_keyboard.Key.ctrl_r,
        }

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
        if key is None:
            return False
        if isinstance(key, pynput_keyboard.KeyCode):
            if key.char == ";":
                return True
            vk = getattr(key, "vk", None)
            return vk in (186,)
        return False

    def _handle_press(
        self, key: Optional[pynput_keyboard.Key | pynput_keyboard.KeyCode]
    ) -> None:
        triggered = False
        now = time.monotonic()

        with self._lock:
            try:
                if key is None:
                    return
                if key == pynput_keyboard.Key.alt_gr:
                    self._state["altgr"] = True
                    self._state["alt"] = True
                    self._state["ctrl"] = True
                    self._last_press["altgr"] = now
                    self._last_press["alt"] = now
                    self._last_press["ctrl"] = now
                elif key in self._alt_keys:
                    self._state["alt"] = True
                    self._last_press["alt"] = now
                elif key in self._ctrl_keys:
                    self._state["ctrl"] = True
                    self._last_press["ctrl"] = now
                elif isinstance(key, pynput_keyboard.KeyCode) and key.char is None:
                    pass

                if self._is_semicolon(key):
                    if not self._state["semicolon"]:
                        self._state["semicolon"] = True
                    self._last_press["semicolon"] = now

                modifier_active = self._state["altgr"] or (
                    self._state["alt"] and self._state["ctrl"]
                )
                modifier_recent = (
                    now - self._last_press["altgr"] <= config.HOTKEY_SEQUENCE_WINDOW
                    or (
                        now - self._last_press["alt"] <= config.HOTKEY_SEQUENCE_WINDOW
                        and now - self._last_press["ctrl"] <= config.HOTKEY_SEQUENCE_WINDOW
                    )
                )
                semicolon_recent = (
                    now - self._last_press["semicolon"] <= config.HOTKEY_SEQUENCE_WINDOW
                )

                if (
                    not self._state["consumed"]
                    and (
                        (
                            self._is_semicolon(key)
                            and (modifier_active or modifier_recent)
                        )
                        or (
                            key == pynput_keyboard.Key.alt_gr
                            and (self._state["semicolon"] or semicolon_recent)
                        )
                        or (
                            key in self._alt_keys
                            and self._state["ctrl"]
                            and (self._state["semicolon"] or semicolon_recent)
                        )
                        or (
                            key in self._ctrl_keys
                            and self._state["alt"]
                            and (self._state["semicolon"] or semicolon_recent)
                        )
                    )
                ):
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
                if key == pynput_keyboard.Key.alt_gr:
                    self._state["altgr"] = False
                    self._state["alt"] = False
                    self._state["ctrl"] = False
                elif key in self._alt_keys:
                    self._state["alt"] = False
                elif key in self._ctrl_keys:
                    self._state["ctrl"] = False

                if self._is_semicolon(key):
                    self._state["semicolon"] = False
                    self._state["consumed"] = False
                elif not self._state["semicolon"]:
                    if (
                        key in self._alt_keys
                        or key in self._ctrl_keys
                        or key == pynput_keyboard.Key.alt_gr
                    ):
                        self._state["consumed"] = False

            except AttributeError:
                pass
