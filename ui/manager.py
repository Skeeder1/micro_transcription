"""Visualizer process management."""

from __future__ import annotations

import os
import subprocess
import sys
import time

from shared import config
from shared.context import AppContext


def start_visualizer(ctx: AppContext) -> None:
    """Start the visualizer process if not already running."""
    with ctx.visualizer_lock:
        if ctx.visualizer_proc and ctx.visualizer_proc.poll() is None:
            print("[Visualizer] Déjà actif, skip")
            return

        if ctx.visualizer_proc:
            ctx.visualizer_proc = None

        # Determine Python executable to use
        exe = os.environ.get("PYTHON_EXE", sys.executable)

        # Windows-specific: prefer pythonw.exe to hide console
        if sys.platform == "win32" and exe.endswith("python.exe"):
            pythonw_exe = exe.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw_exe):
                exe = pythonw_exe

        # Platform-specific subprocess configuration
        startupinfo = None
        creationflags = 0
        env = os.environ.copy()

        if sys.platform == "win32":
            # Windows: hide console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            creationflags = 0x08000000 | 0x00000008  # CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
        else:
            # Linux: Force X11 (XWayland) instead of Wayland native
            # This is required for WindowStaysOnTopHint to work correctly
            env["QT_QPA_PLATFORM"] = "xcb"

            # Force software rendering for QtWebEngine
            # Disable all OpenGL/GPU features to avoid errors
            env["QT_XCB_GL_INTEGRATION"] = "none"
            env["QT_QUICK_BACKEND"] = "software"
            env["LIBGL_ALWAYS_SOFTWARE"] = "1"
            env["QT_OPENGL"] = "software"
            env["QMLSCENE_DEVICE"] = "softwarecontext"
            # Chromium flags for WebEngine - comprehensive software rendering
            env["QTWEBENGINE_CHROMIUM_FLAGS"] = (
                "--disable-gpu "
                "--disable-gpu-compositing "
                "--disable-gpu-rasterization "
                "--disable-software-rasterizer "
                "--disable-webgl "
                "--disable-accelerated-2d-canvas "
                "--disable-accelerated-video-decode "
                "--in-process-gpu "
                "--disable-features=VizDisplayCompositor"
            )

        try:
            # Use the new visualizer app path
            ctx.visualizer_proc = subprocess.Popen(
                [exe, "-m", "ui.visualizer_app", str(config.SSE_PORT)],
                startupinfo=startupinfo,
                creationflags=creationflags,
                env=env,
            )
            print(f"[Visualizer] Lancé (PID: {ctx.visualizer_proc.pid})")
        except Exception as exc:
            print(f"[Visualizer] Erreur lancement: {exc}")
            ctx.visualizer_proc = None

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
