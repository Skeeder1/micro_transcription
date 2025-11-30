"""Core transcription engine - Application bootstrap and orchestration."""

from __future__ import annotations

import contextlib
import sys
import threading
import time
import urllib.request
from typing import Optional

import sounddevice as sd

from shared import config
from shared.context import AppContext
from shared.hotkey import HotkeyManager
from shared.sleep import toggle_sleep_mode
from shared.logger import init_logger, log_info, log_warn, log_error
from api.server import broadcast_preview, start_server
from ui.manager import start_visualizer, stop_visualizer
from core.audio_capture import make_audio_callback
from core.models import init_models
from core.processor import run as run_main_loop

# System tray support (optional)
try:
    from ui.system_tray import SystemTrayManager, is_system_tray_available
    SYSTEM_TRAY_AVAILABLE = True
except ImportError:
    SYSTEM_TRAY_AVAILABLE = False
    SystemTrayManager = None  # type: ignore
    is_system_tray_available = lambda: False  # type: ignore


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
    # Configure UTF-8 encoding for Windows console (only if console exists)
    if sys.platform == "win32":
        import io
        # pythonw.exe n'a pas de console, stdout/stderr peuvent être None
        if sys.stdout is not None and hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if sys.stderr is not None and hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

    # Initialiser le logger en premier (logs persistants même avec pythonw.exe)
    init_logger()

    ctx = AppContext()

    # Vérifier que last_speech_time est bien initialisé à maintenant
    log_info(f"[Init] AppContext created at {time.strftime('%H:%M:%S', time.localtime(ctx.last_speech_time))}")
    log_info(f"[Init] Current time is {time.strftime('%H:%M:%S', time.localtime(time.time()))}")
    delta = time.time() - ctx.last_speech_time
    if delta > 1.0:
        log_info(f"[Init] WARNING: last_speech_time is {delta:.1f}s in the past!")

    log_info("=" * 70)
    log_info("🎤 SYSTÈME DE DICTÉE VOCALE AVANCÉ v2.0")
    log_info("=" * 70)

    # Initialiser le détecteur de voix (si activé)
    if getattr(config, "ENABLE_ADVANCED_VAD", False):
        try:
            from core.voice_detector import VoiceDetector
        except ImportError as e:
            log_warn(f"⚠️ Impossible d'importer VoiceDetector: {e}")
            log_warn("   Installation requise: pip install torch torchaudio onnxruntime")
            log_warn("   → Utilisation du mode RMS basique")
            ctx.voice_detector = None
        else:
            use_adaptive = getattr(config, "USE_ADAPTIVE_DETECTION", True)
            mode_str = "adaptatif" if use_adaptive else "seuils fixes"
            log_info(f"🎯 Initialisation détecteur vocal avancé (mode {mode_str})...")
            try:
                ctx.voice_detector = VoiceDetector(
                    sample_rate=config.SAMPLE_RATE,
                    silero_threshold=getattr(config, "SILERO_THRESHOLD", 0.5),
                    rms_threshold=config.ENERGY_THRESHOLD,
                    use_zcr_filter=getattr(config, "USE_ZCR_FILTER", True),
                    zcr_min=getattr(config, "ZCR_MIN", 0.02),
                    zcr_max=getattr(config, "ZCR_MAX", 0.30),
                    use_adaptive=use_adaptive,
                    adaptive_boost_factor=getattr(config, "ADAPTIVE_BOOST_FACTOR", 2.5),
                    adaptive_window_seconds=getattr(config, "ADAPTIVE_WINDOW_SECONDS", 3.0),
                )
                if use_adaptive:
                    log_info(f"   → Mode adaptatif: boost={getattr(config, 'ADAPTIVE_BOOST_FACTOR', 2.5)}x")
                    log_info("   → Calibration automatique du bruit ambiant (2 premières secondes)")
                else:
                    log_info("   → Mode seuils fixes: Silero + ZCR")
            except Exception as e:
                log_warn(f"⚠️ Impossible d'initialiser le VAD avancé: {e}")
                log_warn("   → Utilisation du mode RMS basique")
                ctx.voice_detector = None
    else:
        log_info("🔊 Utilisation détection RMS basique (mode legacy)")

    # Démarrer le serveur API SSE (daemon thread)
    log_info("🌐 Démarrage serveur API SSE...")
    start_server(ctx)

    # ATTENDRE que le serveur SSE soit VRAIMENT prêt avant de lancer l'UI
    # Cela évite que l'UI apparaisse "grise" car le SSE n'est pas encore prêt
    log_info("⏳ Attente que le serveur SSE soit prêt...")
    sse_ready = False
    max_attempts = 50  # 50 * 0.2s = 10 secondes max
    for attempt in range(max_attempts):
        try:
            response = urllib.request.urlopen(
                f"http://{config.SSE_HOST}:{config.SSE_PORT}/ping", timeout=1
            )
            if response.read().decode().strip() == "pong":
                log_info("✅ Serveur API prêt!")
                sse_ready = True
                break
        except Exception:
            pass  # Serveur pas encore prêt
        time.sleep(0.2)  # Attendre 200ms avant retry

    if not sse_ready:
        log_error("❌ Timeout: Serveur SSE n'a pas démarré après 10s")
        log_error("   L'UI va être lancée mais le preview ne fonctionnera probablement pas")

    # Lancer le visualiseur maintenant que le SSE est prêt
    log_info("🚀 Lancement interface graphique...")
    start_visualizer(ctx)
    time.sleep(0.5)  # Laisser le temps à l'UI de se connecter au SSE

    hotkey = HotkeyManager(lambda: toggle_sleep_mode(ctx))
    hotkey.start()

    # Initialiser le system tray si activé et disponible
    tray_manager = None
    if config.ENABLE_SYSTEM_TRAY and SYSTEM_TRAY_AVAILABLE:
        if is_system_tray_available():
            log_info("🎨 Initialisation system tray...")
            try:
                def quit_app():
                    """Callback pour quitter l'application depuis le tray."""
                    log_info("⏹️ Arrêt demandé depuis le system tray")
                    raise KeyboardInterrupt()

                tray_manager = SystemTrayManager(
                    ctx,
                    on_sleep_toggle=lambda: toggle_sleep_mode(ctx),
                    on_quit=quit_app,
                )
                tray_manager.show()
                log_info("✅ System tray activé")
            except Exception as exc:
                log_warn(f"⚠️ Impossible d'activer le system tray: {exc}")
                tray_manager = None
        else:
            log_warn("⚠️ System tray non supporté par votre environnement de bureau")
    elif config.ENABLE_SYSTEM_TRAY and not SYSTEM_TRAY_AVAILABLE:
        log_warn("⚠️ System tray activé dans config mais PySide6 non disponible")

    # Charger les modèles uniquement si la transcription est activée
    if config.ENABLE_TRANSCRIPTION:
        # Charger les modèles en ARRIÈRE-PLAN pendant que l'UI est visible
        models_ready = threading.Event()
        models_error: list[Optional[Exception]] = [None]  # Liste pour stocker l'erreur éventuelle

        def load_models_async():
            try:
                log_info("📥 Chargement modèles en arrière-plan...")
                broadcast_preview(ctx, f"⏳ Chargement modèle Whisper '{config.WHISPER_MODEL}'...")
                broadcast_preview(ctx, "   Cela peut prendre quelques secondes...")
                init_models(ctx)
                broadcast_preview(ctx, "✅ Modèles chargés - Système prêt!")
                log_info("✅ Chargement des modèles terminé avec succès")
                models_ready.set()
            except Exception as exc:
                log_error(f"❌ Impossible de charger les modèles Whisper: {exc}")
                broadcast_preview(ctx, f"❌ ERREUR: Échec du chargement des modèles - {str(exc)[:100]}")
                models_error[0] = exc
                models_ready.set()

        threading.Thread(target=load_models_async, daemon=True, name="ModelLoader").start()

        # Attendre que les modèles soient chargés avant de traiter l'audio
        log_info("⏳ Préparation du système...")
        models_ready.wait()

        if models_error[0] is not None:
            log_error("❌ Échec chargement modèles, arrêt...")
            hotkey.stop()
            stop_visualizer(ctx)
            ctx.shutdown()
            return 1

        log_info("🔊 Système prêt - Parlez maintenant!")
    else:
        # Mode visualiseur uniquement - pas besoin d'attendre
        log_info("🌊 Mode visualiseur actif - Prêt immédiatement!")
        broadcast_preview(ctx, "🌊 Visualiseur prêt (transcription désactivée)")

    # Démarrer la capture audio
    log_info("🎤 Démarrage capture audio...")
    try:
        audio_stream = _configure_audio_stream(ctx)
    except Exception as exc:
        log_error(f"❌ Impossible de démarrer la capture audio: {exc}")
        log_error("   Vérifiez que:")
        log_error("   - Un microphone est branché")
        log_error("   - Le micro n'est pas utilisé par une autre application")
        log_error("   - Les permissions microphone sont accordées")
        try:
            log_info("   Micros disponibles:")
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    log_info(f"     [{i}] {dev['name']}")
        except Exception:
            pass
        hotkey.stop()
        stop_visualizer(ctx)
        ctx.shutdown()
        return 1

    try:
        with audio_stream:
            log_info("✅ Capture audio démarrée")
            run_main_loop(ctx)
    except KeyboardInterrupt:
        log_info("\n⏹️ Interruption utilisateur")
    except Exception as exc:
        log_error(f"❌ Erreur inattendue: {exc}")
        import traceback
        log_error(traceback.format_exc())
        return 1
    finally:
        hotkey.stop()

        # Nettoyer le system tray si initialisé
        if tray_manager is not None:
            try:
                tray_manager.cleanup()
            except Exception:
                pass

        stop_visualizer(ctx)

        # Décharger le détecteur vocal si présent
        if ctx.voice_detector is not None:
            try:
                ctx.voice_detector.unload_model()
            except Exception:
                pass

        ctx.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(run())
