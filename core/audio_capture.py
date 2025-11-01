"""Audio acquisition helpers."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Optional, TYPE_CHECKING

import numpy as np
import pyperclip
from pynput import keyboard as pynput_keyboard

from shared import config
from shared.context import AppContext

if TYPE_CHECKING:
    from .voice_detector import VoiceDetector


_keyboard_controller = pynput_keyboard.Controller()


def _detect_linux_environment() -> tuple[str, bool]:
    """
    Detect Linux display server environment.

    Returns:
        Tuple of (environment_type, xdotool_available)
        environment_type: "X11", "Wayland", or "unknown"
    """
    if sys.platform != "linux":
        return ("unknown", False)

    # Check for Wayland
    if os.environ.get("WAYLAND_DISPLAY"):
        env_type = "Wayland"
    elif os.environ.get("DISPLAY"):
        env_type = "X11"
    else:
        env_type = "unknown"

    # Check if xdotool is available
    xdotool_available = subprocess.run(
        ["which", "xdotool"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0

    return (env_type, xdotool_available)


def make_audio_callback(ctx: AppContext):
    """Return an input stream callback bound to the context."""

    def _callback(indata, frames, time_info, status):  # type: ignore[override]
        if status:
            print(f"⚠️ Audio status: {status}")

        # Ne capturer l'audio QUE si le système est actif (pas en veille)
        with ctx.sleep_lock:
            if ctx.is_sleeping:
                return  # Ignore audio pendant la veille

        ctx.audio_queue.put(indata.copy())

    return _callback


def detect_activity(
    audio_block: np.ndarray,
    voice_detector: Optional[VoiceDetector] = None
) -> bool:
    """
    Detect voice activity using advanced VAD or legacy RMS.

    Args:
        audio_block: Audio chunk to analyze
        voice_detector: Optional VoiceDetector instance for advanced detection

    Returns:
        True if voice detected, False if silence or ambient noise
    """
    # Advanced VAD mode (Silero + ZCR)
    if getattr(config, "ENABLE_ADVANCED_VAD", False) and voice_detector is not None:
        debug = getattr(config, "DEBUG_VAD", False)
        return voice_detector.is_human_speech(audio_block, debug=debug)

    # Legacy mode: simple RMS threshold
    rms = float(np.sqrt(np.mean(np.square(audio_block), dtype=np.float64)))

    # Mode debug pour diagnostiquer les problèmes de détection
    if getattr(config, "DEBUG_AUDIO_LEVEL", False):
        is_active = rms > config.ENERGY_THRESHOLD
        status = "✓ ACTIVE" if is_active else "  silent"
        print(f"\r[AUDIO] RMS={rms:.6f} threshold={config.ENERGY_THRESHOLD} → {status}", end="", flush=True)

    return rms > config.ENERGY_THRESHOLD


def _paste_linux_xdotool(text: str) -> bool:
    """
    Paste text using xdotool (Linux X11 native).

    Args:
        text: Text to paste

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use xdotool to type the text directly (more reliable than clipboard)
        # --clearmodifiers ensures clean state (no stuck Shift/Ctrl)
        # --delay controls typing speed (0 = instant)
        result = subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "0", "--", text],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as exc:
        print(f"⚠️ Erreur xdotool: {exc}")
        return False


def _paste_linux_clipboard(text: str) -> bool:
    """
    Paste text using clipboard + xdotool key simulation (fallback).

    Args:
        text: Text to paste

    Returns:
        True if successful, False otherwise
    """
    try:
        # Copy to clipboard
        pyperclip.copy(text)
        time.sleep(0.1)

        # Use xdotool to send Ctrl+V
        result = subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception as exc:
        print(f"⚠️ Erreur paste clipboard Linux: {exc}")
        return False


def _paste_windows_pynput(text: str) -> bool:
    """
    Paste text using pyperclip + pynput (Windows method).

    Args:
        text: Text to paste

    Returns:
        True if successful, False otherwise
    """
    try:
        pyperclip.copy(text)
        time.sleep(0.1)

        _keyboard_controller.press(pynput_keyboard.Key.ctrl)
        _keyboard_controller.press("v")
        _keyboard_controller.release("v")
        _keyboard_controller.release(pynput_keyboard.Key.ctrl)
        return True
    except Exception as exc:
        print(f"⚠️ Erreur paste Windows: {exc}")
        return False


def paste_via_clipboard(ctx: AppContext, text: str) -> None:
    """
    Paste text into the active window using platform-specific method.

    Strategy:
    - Linux X11: Use xdotool native typing (most reliable)
    - Linux Wayland: Fallback to clipboard + pynput
    - Windows: Use pyperclip + pynput (original method)

    Args:
        ctx: Application context
        text: Text to paste
    """
    if not text or text == ctx.last_pasted:
        return

    payload = text + (" " if config.APPEND_SPACE and not text.endswith(" ") else "")
    old_clip: Optional[str] = None

    # Save clipboard if restoration is enabled
    if config.RESTORE_CLIPBOARD:
        try:
            old_clip = pyperclip.paste()
        except pyperclip.PyperclipException:
            old_clip = None

    time.sleep(config.PASTE_DELAY_SECONDS)

    success = False

    # Platform-specific paste logic
    if sys.platform == "linux":
        env_type, xdotool_available = _detect_linux_environment()

        if env_type == "X11" and xdotool_available:
            # Best method for Linux X11: direct typing with xdotool
            print(f"[Paste] Utilisation xdotool (X11) pour coller {len(payload)} caracteres")
            success = _paste_linux_xdotool(payload)

            if not success:
                # Fallback to clipboard method
                print("[Paste] Fallback: xdotool clipboard method")
                success = _paste_linux_clipboard(payload)
        else:
            # Wayland or xdotool not available
            if env_type == "Wayland":
                print(f"[Paste] Environnement Wayland detecte, utilisation pynput")
            else:
                print(f"[Paste] xdotool non disponible, utilisation pynput")

            # Use pynput as fallback (works on Wayland with some limitations)
            try:
                pyperclip.copy(payload)
                time.sleep(0.1)

                _keyboard_controller.press(pynput_keyboard.Key.ctrl)
                _keyboard_controller.press("v")
                _keyboard_controller.release("v")
                _keyboard_controller.release(pynput_keyboard.Key.ctrl)
                success = True
            except Exception as exc:
                print(f"⚠️ Erreur paste pynput (Linux): {exc}")
                print("   Installez xdotool pour un meilleur support: sudo apt install xdotool")

    elif sys.platform == "win32":
        # Windows: use original method
        success = _paste_windows_pynput(payload)

    else:
        # Other platforms: try pynput
        print(f"[Paste] Plateforme {sys.platform} non testee, utilisation pynput")
        success = _paste_windows_pynput(payload)

    # Restore clipboard if enabled and paste was successful
    if success and config.RESTORE_CLIPBOARD and old_clip is not None:
        time.sleep(0.05)
        try:
            pyperclip.copy(old_clip)
        except Exception:
            pass  # Silent fail on clipboard restoration

    if success:
        ctx.last_pasted = text
    else:
        print("❌ Echec du collage du texte")
