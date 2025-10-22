"""Application bootstrap and orchestration."""

from __future__ import annotations

import contextlib
import sys
import threading
import time
import urllib.request
from typing import Optional

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
    
    # Démarrer le serveur SSE sans attendre
    start_server(ctx)
    
    # Lancer le visualiseur IMMÉDIATEMENT (UI apparaît tout de suite)
    print("🚀 Lancement interface graphique...")
    start_visualizer(ctx)
    time.sleep(0.3)  # Juste le temps que la fenêtre s'ouvre
    
    # Vérifier le serveur SSE en arrière-plan
    def check_sse():
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
    
    threading.Thread(target=check_sse, daemon=True, name="SSECheck").start()

    hotkey = HotkeyManager(lambda: toggle_sleep_mode(ctx))
    hotkey.start()

    # Charger les modèles uniquement si la transcription est activée
    if config.ENABLE_TRANSCRIPTION:
        # Charger les modèles en ARRIÈRE-PLAN pendant que l'UI est visible
        models_ready = threading.Event()
        models_error: list[Optional[Exception]] = [None]  # Liste pour stocker l'erreur éventuelle
        
        def load_models_async():
            try:
                print("📥 Chargement modèles en arrière-plan...")
                broadcast_preview(ctx, "⏳ Chargement des modèles IA...")
                init_models(ctx)
                broadcast_preview(ctx, "✅ Modèles chargés - Système prêt!")
                models_ready.set()
            except Exception as exc:
                print(f"❌ Impossible de charger les modèles Whisper: {exc}")
                models_error[0] = exc
                models_ready.set()
        
        threading.Thread(target=load_models_async, daemon=True, name="ModelLoader").start()

        # Attendre que les modèles soient chargés avant de traiter l'audio
        print("⏳ Préparation du système...")
        models_ready.wait()
        
        if models_error[0] is not None:
            print("❌ Échec chargement modèles, arrêt...")
            hotkey.stop()
            stop_visualizer(ctx)
            ctx.shutdown()
            return 1
        
        print("🔊 Système prêt - Parlez maintenant!")
    else:
        # Mode visualiseur uniquement - pas besoin d'attendre
        print("🌊 Mode visualiseur actif - Prêt immédiatement!")
        broadcast_preview(ctx, "🌊 Visualiseur prêt (transcription désactivée)")

    try:

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
