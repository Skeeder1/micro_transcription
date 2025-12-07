"""Audio acquisition helpers.

This module handles audio capture callbacks and paste operations with
platform-specific implementations for Linux/Windows.

Phase 4 Integration:
- Uses error handling decorators for robust paste operations
- Thread-safe paste operations with TimeoutLock
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import threading
from typing import Optional, TYPE_CHECKING

import numpy as np
import pyperclip
from pynput import keyboard as pynput_keyboard

from shared import config
from shared.constants import LOG_PREFIX_AUDIO, LOG_PREFIX_PASTE, PASTE_LOCK_TIMEOUT
from shared.context import AppContext
from shared.logger import log_info, log_warn, log_error
from shared.errors import handle_errors
from shared.threading_utils import TimeoutLock

if TYPE_CHECKING:
    from .voice_detector import VoiceDetector


_keyboard_controller = pynput_keyboard.Controller()

# Thread-safe lock for paste operations to prevent concurrent paste conflicts
_paste_lock = TimeoutLock(timeout=PASTE_LOCK_TIMEOUT, name="paste_lock")


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
            log_warn(f"{LOG_PREFIX_AUDIO} status: {status}")

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
    Detect voice activity using advanced VAD or legacy RMS + ZCR.

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

    # Legacy mode: RMS threshold + optional ZCR filter
    from shared.audio_utils import calculate_zcr

    # Flatten audio if needed
    audio_flat = audio_block.squeeze() if audio_block.ndim > 1 else audio_block

    rms = float(np.sqrt(np.mean(np.square(audio_flat), dtype=np.float64)))
    is_above_threshold = rms > config.ENERGY_THRESHOLD

    # Apply ZCR filter if enabled (distinguishes speech from noise)
    use_zcr = getattr(config, "USE_ZCR_FILTER", False)
    zcr_valid = True

    if use_zcr and is_above_threshold:
        zcr = calculate_zcr(audio_flat)
        zcr_min = getattr(config, "ZCR_MIN", 0.02)
        zcr_max = getattr(config, "ZCR_MAX", 0.30)
        zcr_valid = zcr_min <= zcr <= zcr_max

    is_active = is_above_threshold and zcr_valid

    # Mode debug pour diagnostiquer les problèmes de détection
    if getattr(config, "DEBUG_AUDIO_LEVEL", False):
        if use_zcr and is_above_threshold:
            zcr = calculate_zcr(audio_flat)
            status = "VOICE" if is_active else f"NOISE (ZCR={zcr:.3f})"
        else:
            status = "ACTIVE" if is_active else "silent"
        log_info(f"{LOG_PREFIX_AUDIO} RMS={rms:.6f} threshold={config.ENERGY_THRESHOLD} -> {status}")

    return is_active


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
            log_warn(f"{LOG_PREFIX_PASTE} xdotool stderr: {result.stderr}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log_warn(f"{LOG_PREFIX_PASTE} xdotool timeout (10s)")
        return False
    except FileNotFoundError:
        log_warn(f"{LOG_PREFIX_PASTE} xdotool non trouvé")
        return False
    except Exception as exc:
        log_warn(f"{LOG_PREFIX_PASTE} Erreur xdotool: {exc}")
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
        log_warn(f"{LOG_PREFIX_PASTE} Erreur paste clipboard Linux: {exc}")
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
        log_warn(f"{LOG_PREFIX_PASTE} Erreur paste Windows: {exc}")
        return False


@handle_errors(log_prefix=LOG_PREFIX_PASTE, reraise=False)
def paste_via_clipboard(ctx: AppContext, text: str) -> None:
    """
    Paste text into the active window using platform-specific method.

    Strategy:
    - Linux X11: Use xdotool native typing (most reliable)
    - Linux Wayland: Fallback to clipboard + pynput
    - Windows: Use pyperclip + pynput (original method)

    Thread-safe: Uses TimeoutLock to prevent concurrent paste operations.

    Args:
        ctx: Application context
        text: Text to paste
    """
    if not text or text == ctx.last_pasted:
        return

    # Use timeout lock to prevent concurrent paste operations
    with _paste_lock:
        _paste_text_impl(ctx, text)


def _paste_text_impl(ctx: AppContext, text: str) -> None:
    """Internal implementation of paste operation (runs under lock)."""
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
            log_info(f"{LOG_PREFIX_PASTE} Utilisation xdotool ({method}) pour coller {len(payload)} caractères")
            success = _paste_linux_xdotool(payload)

            if not success:
                # Fallback to clipboard method
                log_info(f"{LOG_PREFIX_PASTE} Fallback: xdotool clipboard method")
                success = _paste_linux_clipboard(payload)
        else:
            # No xdotool or no DISPLAY - use pynput as last resort
            log_info(f"{LOG_PREFIX_PASTE} Environnement {env_type}, xdotool indisponible, utilisation pynput")

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
                log_warn(f"{LOG_PREFIX_PASTE} Erreur paste pynput (Linux): {exc}")
                log_warn(f"{LOG_PREFIX_PASTE} Installez xdotool pour un meilleur support: sudo apt install xdotool")

    elif sys.platform == "win32":
        # Windows: use original method
        success = _paste_windows_pynput(payload)

    else:
        # Other platforms: try pynput
        log_info(f"{LOG_PREFIX_PASTE} Plateforme {sys.platform} non testée, utilisation pynput")
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
        log_warn(f"{LOG_PREFIX_PASTE} Échec du collage du texte")
