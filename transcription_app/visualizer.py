"""Visualizer process management."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from . import config
from .context import AppContext


def start_visualizer(ctx: AppContext) -> None:
    """Start the visualizer process if not already running."""
    with ctx.visualizer_lock:
        if ctx.visualizer_proc and ctx.visualizer_proc.poll() is None:
            print("[Visualizer] Déjà actif, skip")
            return

        if ctx.visualizer_proc:
            ctx.visualizer_proc = None

        exe = os.environ.get("PYTHON_EXE", sys.executable)
        if exe.endswith("python.exe"):
            pythonw_exe = exe.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw_exe):
                exe = pythonw_exe

        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = 0x08000000 | 0x00000008

        try:
            ctx.visualizer_proc = subprocess.Popen(
                [exe, "mic_visualizer_enhanced.py", str(config.SSE_PORT)],
                startupinfo=startupinfo,
                creationflags=creationflags,
            )
            print(f"[Visualizer] Lancé (PID: {ctx.visualizer_proc.pid})")
        except Exception as exc:
            print(f"[Visualizer] Erreur lancement: {exc}")
            ctx.visualizer_proc = None

    # Délai minimal réduit pour apparition plus rapide
    time.sleep(config.VISUALIZER_START_DELAY)


def stop_visualizer(ctx: AppContext) -> None:
    """Terminate the visualizer process if running."""
    with ctx.visualizer_lock:
        if not ctx.visualizer_proc:
            return

        if ctx.visualizer_proc.poll() is not None:
            print(f"[Visualizer] Déjà terminé (PID: {ctx.visualizer_proc.pid})")
            ctx.visualizer_proc = None
            return

        print(f"[Visualizer] Arrêt (PID: {ctx.visualizer_proc.pid})...")
        ctx.visualizer_proc.terminate()
        try:
            ctx.visualizer_proc.wait(timeout=config.VISUALIZER_STOP_TIMEOUT)
            print("[Visualizer] Arrêté proprement")
        except subprocess.TimeoutExpired:
            print("[Visualizer] Force kill (timeout)...")
            ctx.visualizer_proc.kill()
            try:
                ctx.visualizer_proc.wait(timeout=config.VISUALIZER_KILL_TIMEOUT)
            except Exception:
                pass
        except Exception as exc:
            print(f"[Visualizer] Erreur arrêt: {exc}")
        finally:
            ctx.visualizer_proc = None
