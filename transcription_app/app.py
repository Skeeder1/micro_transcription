"""Application bootstrap and orchestration."""

from __future__ import annotations

import contextlib
import sys
import threading
import time
from typing import Optional

import sounddevice as sd

from . import config
from .audio import make_audio_callback
from .context import AppContext
from .hotkey import HotkeyManager
from .main_loop import run as run_main_loop
from .models import init_models
from .sleep import toggle_sleep_mode
from .state_manager import get_state_manager


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
    print("🎤 SYSTÈME DE DICTÉE VOCALE AVANCÉ (Module Indépendant)")
    print("=" * 70)
    print()
    print("ℹ️  Le visualiseur est optionnel et complètement indépendant")
    print("   Lancez-le séparément si vous voulez voir les ondes:")
    print("   python run_visualizer.py")
    print()

    # Initialiser le gestionnaire d'état partagé
    state_mgr = get_state_manager()

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
                state_mgr.update_preview("⏳ Chargement des modèles IA...")
                init_models(ctx)
                state_mgr.update_preview("✅ Modèles chargés - Système prêt!")
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
            ctx.shutdown()
            return 1
        
        print("🔊 Système prêt - Parlez maintenant!")
    else:
        # Mode visualiseur uniquement - pas besoin d'attendre
        print("🌊 Mode écoute actif - Prêt immédiatement!")
        state_mgr.update_preview("🌊 Écoute audio active (transcription désactivée)")

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
        ctx.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(run())
