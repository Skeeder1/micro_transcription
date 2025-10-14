"""Application bootstrap and orchestration."""

from __future__ import annotations

import contextlib
import sys
import time
import urllib.request

import sounddevice as sd

from . import config
from .audio import make_audio_callback
from .context import AppContext
from .hotkey import HotkeyManager
from .main_loop import run as run_main_loop
from .models import init_models
from .sleep import toggle_sleep_mode
from .sse import broadcast_preview, start_server
from .visualizer import start_visualizer, stop_visualizer


def _configure_audio_stream(ctx: AppContext) -> contextlib.AbstractContextManager:
    blocksize = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)
    callback = make_audio_callback(ctx)
    return sd.InputStream(
        samplerate=config.SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=blocksize,
        callback=callback,
    )


def run() -> int:
    ctx = AppContext()
    print("=" * 70)
    print("🎤 SYSTÈME DE DICTÉE VOCALE AVANCÉ")
    print("=" * 70)
    start_server(ctx)
    time.sleep(1.0)

    try:
        response = urllib.request.urlopen(
            f"http://{config.SSE_HOST}:{config.SSE_PORT}/ping", timeout=2
        )
        if response.read().decode().strip() == "pong":
            print("✅ Serveur SSE opérationnel")
        else:
            print("⚠️ Réponse inattendue du serveur SSE")
    except Exception as exc:
        print(f"❌ Serveur SSE indisponible: {exc}")
        print("⚠️ Le preview ne fonctionnera pas tant que le serveur est hors ligne")

    hotkey = HotkeyManager(lambda: toggle_sleep_mode(ctx))
    hotkey.start()

    try:
        init_models(ctx)
    except Exception as exc:
        print(f"❌ Impossible de charger les modèles Whisper: {exc}")
        hotkey.stop()
        ctx.shutdown()
        return 1

    try:
        start_visualizer(ctx)
        time.sleep(config.VISUALIZER_READY_DELAY)
        print("[TEST] Envoi message de test SSE...")
        broadcast_preview(ctx, "🔊 Système prêt - Parlez maintenant!")

        with _configure_audio_stream(ctx):
            run_main_loop(ctx)
    except KeyboardInterrupt:
        print("\n⏹️ Interruption utilisateur")
    except Exception as exc:
        print(f"❌ Erreur inattendue: {exc}")
        return 1
    finally:
        hotkey.stop()
        stop_visualizer(ctx)
        ctx.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(run())
