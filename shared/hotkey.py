"""Hotkey management using pynput.

This module handles keyboard hotkeys for the transcription system:
- F8: Toggle microphone recording
- F9: Toggle system sleep mode

Phase 4 Integration:
- Uses error handling for robust hotkey processing
- Hotkey actions trigger events via sleep.py's toggle functions
"""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional, Dict

from pynput import keyboard as pynput_keyboard

from shared.constants import LOG_PREFIX_HOTKEY
from shared.logger import log_error, log_info
from shared.errors import handle_errors


class HotkeyManager:
    """
    Listens for hotkeys to control the dictaphone.

    Hotkeys:
    - F8: Toggle recording (microphone on/off)
    - F9: Toggle sleep mode
    """

    def __init__(
        self,
        on_toggle_sleep: Callable[[], None],
        on_toggle_recording: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_toggle_sleep = on_toggle_sleep
        self._on_toggle_recording = on_toggle_recording
        self._listener: Optional[pynput_keyboard.Listener] = None
        self._lock = threading.Lock()
        self._state: Dict[str, bool] = {"f8_consumed": False, "f9_consumed": False}
        self._last_press_time: Dict[str, float] = {"f8": 0.0, "f9": 0.0}

    @handle_errors(log_prefix=LOG_PREFIX_HOTKEY, reraise=False)
    def start(self) -> None:
        """Start listening for hotkeys."""
        if self._listener is not None:
            return
        self._listener = pynput_keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
            suppress=False,
        )
        self._listener.daemon = True
        self._listener.start()
        log_info(f"{LOG_PREFIX_HOTKEY} Listener démarré")

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
        triggered_f8 = False
        triggered_f9 = False

        with self._lock:
            try:
                if key is None:
                    return

                # F8: Toggle recording
                if key == pynput_keyboard.Key.f8 and self._on_toggle_recording:
                    if self._state.get("f8_consumed", False):
                        time_stuck = time.time() - self._last_press_time.get("f8", 0)
                        if time_stuck > 2.0:
                            self._state["f8_consumed"] = False

                    if not self._state.get("f8_consumed", False):
                        self._state["f8_consumed"] = True
                        self._last_press_time["f8"] = time.time()
                        triggered_f8 = True

                # F9: Toggle sleep
                elif key == pynput_keyboard.Key.f9:
                    if self._state.get("f9_consumed", False):
                        time_stuck = time.time() - self._last_press_time.get("f9", 0)
                        if time_stuck > 2.0:
                            self._state["f9_consumed"] = False

                    if not self._state.get("f9_consumed", False):
                        self._state["f9_consumed"] = True
                        self._last_press_time["f9"] = time.time()
                        triggered_f9 = True

            except AttributeError:
                pass
            except Exception as exc:
                log_error(f"{LOG_PREFIX_HOTKEY} ERROR in press handler: {exc}")
                self._state["f8_consumed"] = False
                self._state["f9_consumed"] = False

        if triggered_f8:
            threading.Thread(
                target=self._on_toggle_recording,
                name="HotkeyRecording",
                daemon=True
            ).start()

        if triggered_f9:
            threading.Thread(
                target=self._on_toggle_sleep,
                name="HotkeySleep",
                daemon=True
            ).start()

    def _handle_release(
        self, key: Optional[pynput_keyboard.Key | pynput_keyboard.KeyCode]
    ) -> None:
        with self._lock:
            try:
                if key is None:
                    return

                if key == pynput_keyboard.Key.f8:
                    self._state["f8_consumed"] = False
                elif key == pynput_keyboard.Key.f9:
                    self._state["f9_consumed"] = False

            except AttributeError:
                pass
            except Exception as exc:
                log_error(f"{LOG_PREFIX_HOTKEY} ERROR in release handler: {exc}")
                self._state["f8_consumed"] = False
                self._state["f9_consumed"] = False
