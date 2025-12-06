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


def _detect_linux_environment() -> tuple[str, bool, bool]:
    """
    Detect Linux display server environment.

    Returns:
        Tuple of (environment_type, xdotool_available, xwayland_available)
        environment_type: "X11", "Wayland", or "unknown"
        xdotool_available: True if xdotool command exists
        xwayland_available: True if DISPLAY is set (XWayland works)
    """
    if sys.platform != "linux":
        return ("unknown", False, False)

    # Detect environment type
    is_wayland = bool(os.environ.get("WAYLAND_DISPLAY"))
    has_display = bool(os.environ.get("DISPLAY"))

    if is_wayland:
        env_type = "Wayland"
    elif has_display:
        env_type = "X11"
    else:
        env_type = "unknown"

    # Check if xdotool is available
    xdotool_available = subprocess.run(
        ["which", "xdotool"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0

    # XWayland is available if DISPLAY is set (even under Wayland)
    xwayland_available = has_display and xdotool_available

    return (env_type, xdotool_available, xwayland_available)


def make_audio_callback(ctx: AppContext):
    """Return an input stream callback bound to the context."""

    def _callback(indata, frames, time_info, status):  # type: ignore[override]
        if status:
            print(f"⚠️ Audio status: {status}")

        # PRIORITÉ 1: Système en veille (F9 OFF) → ignorer tout audio
        with ctx.sleep_lock:
            if ctx.is_sleeping:
                return  # Système OFF: ignorer complètement

        # PRIORITÉ 2: Pause manuelle F8 → ignorer l'audio
        with ctx.recording_lock:
            if not ctx.is_recording:
                return  # Pause F8: ignorer tout audio

        # Enregistrement actif → capturer l'audio
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
        # Ensure DISPLAY is set for XWayland
        env = os.environ.copy()
        if "DISPLAY" not in env:
            env["DISPLAY"] = ":0"

        # Small delay to let focus stabilize
        time.sleep(0.05)

        # Use xdotool to type the text directly (more reliable than clipboard)
        # --clearmodifiers ensures clean state (no stuck Shift/Ctrl)
        # --delay 1 adds tiny delay between chars for reliability
        result = subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "1", "--", text],
            capture_output=True,
            text=True,
            timeout=10,
            env=env
        )
        if result.returncode != 0:
            print(f"⚠️ xdotool stderr: {result.stderr}", flush=True)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("⚠️ xdotool timeout (10s)", flush=True)
        return False
    except FileNotFoundError:
        print("⚠️ xdotool non trouvé", flush=True)
        return False
    except Exception as exc:
        print(f"⚠️ Erreur xdotool: {exc}", flush=True)
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
        env_type, xdotool_available, xwayland_available = _detect_linux_environment()

        # Use xdotool if available - works on X11 AND via XWayland under Wayland
        if xwayland_available:
            method = "XWayland" if env_type == "Wayland" else "X11"
            print(f"[Paste] Utilisation xdotool ({method}) pour coller {len(payload)} caractères", flush=True)
            success = _paste_linux_xdotool(payload)

            if not success:
                # Fallback to clipboard method
                print("[Paste] Fallback: xdotool clipboard method", flush=True)
                success = _paste_linux_clipboard(payload)
        else:
            # No xdotool or no DISPLAY - use pynput as last resort
            print(f"[Paste] Environnement {env_type}, xdotool indisponible, utilisation pynput", flush=True)

            # Use pynput as fallback (limited on Wayland)
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
