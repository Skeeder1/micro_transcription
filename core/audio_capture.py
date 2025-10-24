"""Audio acquisition helpers."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import pyperclip
from pynput import keyboard as pynput_keyboard

from shared import config
from shared.context import AppContext


_keyboard_controller = pynput_keyboard.Controller()


def make_audio_callback(ctx: AppContext):
    """Return an input stream callback bound to the context."""

    def _callback(indata, frames, time_info, status):  # type: ignore[override]
        if status:
            print(f"⚠️ Audio status: {status}")
        ctx.audio_queue.put(indata.copy())

    return _callback


def detect_activity(audio_block: np.ndarray) -> bool:
    """Detect voice activity via RMS energy."""
    rms = float(np.sqrt(np.mean(np.square(audio_block), dtype=np.float64)))
    if getattr(config, "DEBUG_AUTO_SLEEP", False):
        # Afficher une ligne concise sans polluer si désactivé
        print(f"[DEBUG] RMS={rms:.6f} threshold={config.ENERGY_THRESHOLD}")
    return rms > config.ENERGY_THRESHOLD


def paste_via_clipboard(ctx: AppContext, text: str) -> None:
    """Paste text into the active window using the clipboard."""
    if not text or text == ctx.last_pasted:
        return

    payload = text + (" " if config.APPEND_SPACE and not text.endswith(" ") else "")
    old_clip: Optional[str] = None

    if config.RESTORE_CLIPBOARD:
        try:
            old_clip = pyperclip.paste()
        except pyperclip.PyperclipException:
            old_clip = None

    pyperclip.copy(payload)
    time.sleep(config.PASTE_DELAY_SECONDS)

    try:
        _keyboard_controller.press(pynput_keyboard.Key.ctrl)
        _keyboard_controller.press("v")
        _keyboard_controller.release("v")
        _keyboard_controller.release(pynput_keyboard.Key.ctrl)
    except Exception as exc:  # pragma: no cover - defensive logging
        print(f"⚠️ Erreur envoi Ctrl+V: {exc}")

    if config.RESTORE_CLIPBOARD and old_clip is not None:
        time.sleep(0.05)
        pyperclip.copy(old_clip)

    ctx.last_pasted = text
