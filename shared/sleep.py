"""Sleep/awake state management."""

from __future__ import annotations

import time

from shared import config
from shared.context import AppContext


def enter_sleep_mode(ctx: AppContext, manual: bool = False) -> None:
    # Import here to avoid circular imports
    from api.server import broadcast_preview, broadcast_state
    from queue import Empty

    with ctx.sleep_lock:
        if ctx.is_sleeping:
            print("[Veille] Déjà en veille, skip")
            return
        ctx.is_sleeping = True
        ctx.is_deep_sleeping = False
        ctx.sleep_start_time = time.time()
        ctx.manual_sleep = manual

    # Vider la queue audio pour éviter le traitement de blocs obsolètes
    cleared_blocks = 0
    try:
        while True:
            ctx.audio_queue.get_nowait()
            cleared_blocks += 1
    except Empty:
        pass

    if cleared_blocks > 0:
        print(f"[Veille] Queue audio vidée ({cleared_blocks} blocs obsolètes supprimés)")

    print("\n💤 Mode VEILLE activé" + (" (manuel)" if manual else " (auto)"))
    print("   Appuyez sur F9 pour réactiver")
    print(f"   Veille profonde dans {config.DEEP_SLEEP_SECONDS / 60:.0f} minutes...")

    # Au lieu de stopper le visualizer, on change juste son état visuellement
    broadcast_state(ctx, "sleep")
    broadcast_preview(ctx, "💤 Mode veille - Appuyez sur F9")


def enter_deep_sleep_mode(ctx: AppContext) -> None:
    """Entre en veille profonde: décharge modèles et ferme visualizer."""
    from core.models import unload_models
    from ui.manager import stop_visualizer

    with ctx.sleep_lock:
        if ctx.is_deep_sleeping:
            print("[Veille Profonde] Déjà en veille profonde, skip")
            return
        if not ctx.is_sleeping:
            print("[Veille Profonde] Doit être en veille simple d'abord")
            return
        ctx.is_deep_sleeping = True

    print("\n🌙 Mode VEILLE PROFONDE activé")
    print("   → Déchargement des modèles IA...")
    print("   → Fermeture du visualizer...")
    print("   Appuyez sur F9 pour réactiver (délai: ~3-5s)")

    # Décharger les modèles de RAM
    unload_models(ctx)

    # Fermer le visualizer pour économiser ressources
    stop_visualizer(ctx)

    print("   ✅ Veille profonde active - Consommation minimale")


def exit_sleep_mode(ctx: AppContext) -> None:
    from core.models import init_models
    from api.server import broadcast_preview, broadcast_state
    from ui.manager import start_visualizer
    from queue import Empty

    ctx.last_speech_time = time.time()

    was_deep_sleeping = False
    with ctx.sleep_lock:
        if not ctx.is_sleeping:
            print("[Veille] Déjà actif, skip")
            return
        was_deep_sleeping = ctx.is_deep_sleeping
        ctx.is_sleeping = False
        ctx.is_deep_sleeping = False
        ctx.sleep_start_time = 0.0
        ctx.manual_sleep = False

    # Vider la queue audio pour éviter le traitement de vieux blocs accumulés
    cleared_blocks = 0
    try:
        while True:
            ctx.audio_queue.get_nowait()
            cleared_blocks += 1
    except Empty:
        pass

    if cleared_blocks > 0:
        print(f"[Réveil] Queue audio vidée ({cleared_blocks} blocs obsolètes supprimés)")

    print("\n🔊 Mode ACTIF - Système réactivé")

    if was_deep_sleeping:
        # Sortie de veille PROFONDE - recharger ressources
        print("   → Rechargement des modèles IA...")
        broadcast_preview(ctx, "⏳ Rechargement modèles IA...")

        try:
            init_models(ctx)
            print("   ✅ Modèles rechargés")
        except Exception as exc:
            print(f"   ❌ Erreur rechargement modèles: {exc}")
            broadcast_preview(ctx, "❌ Erreur rechargement - Redémarrez")

            # NOUVEAU: Restaurer l'état sleep au lieu de laisser incohérent
            with ctx.sleep_lock:
                ctx.is_sleeping = True
                ctx.is_deep_sleeping = True

            print("   → Système remis en veille suite à l'erreur")
            return

        print("   → Relancement du visualizer...")
        start_visualizer(ctx)
        time.sleep(config.VISUALIZER_START_DELAY)

        broadcast_state(ctx, "active")
        broadcast_preview(ctx, "🔊 Système réactivé - Parlez maintenant!")
        print("[Veille Profonde] Réactivation complète (~3-5s)")
    else:
        # Sortie de veille RAPIDE - réactivation instantanée
        broadcast_state(ctx, "active")
        broadcast_preview(ctx, "🔊 Système réactivé - Parlez maintenant!")
        print("[Veille] Réactivation instantanée complète")


def toggle_sleep_mode(ctx: AppContext) -> None:
    current_time = time.time()
    time_since_toggle = current_time - ctx.last_toggle_time

    if time_since_toggle < config.TOGGLE_COOLDOWN_SECONDS:
        print(
            f"[Toggle] Cooldown actif ({time_since_toggle:.2f}s < {config.TOGGLE_COOLDOWN_SECONDS}s) - Ignoré"
        )
        return

    ctx.last_toggle_time = current_time

    print(f"[Toggle] F9 pressed at {time.strftime('%H:%M:%S', time.localtime(current_time))}")

    with ctx.sleep_lock:
        sleeping = ctx.is_sleeping

    print(f"[Toggle] État actuel: {'VEILLE' if sleeping else 'ACTIF'} → {'ACTIF' if sleeping else 'VEILLE'}")

    try:
        if sleeping:
            exit_sleep_mode(ctx)
        else:
            enter_sleep_mode(ctx, manual=True)
    except Exception as exc:
        print(f"❌ Erreur toggle: {exc}")
        ctx.last_toggle_time = 0.0


def check_auto_sleep(ctx: AppContext) -> None:
    with ctx.sleep_lock:
        if ctx.is_sleeping:
            return

    delta = time.time() - ctx.last_speech_time

    # Logging conditionnel toutes les 5 secondes
    if not hasattr(check_auto_sleep, '_last_log'):
        check_auto_sleep._last_log = 0.0

    if time.time() - check_auto_sleep._last_log > 5.0:
        print(f"[AutoSleep] Delta: {delta:.1f}s / {config.AUTO_SLEEP_SECONDS:.1f}s")
        check_auto_sleep._last_log = time.time()

    if getattr(config, "DEBUG_AUTO_SLEEP", False):
        print(f"[DEBUG] time since last speech: {delta:.2f}s (auto_sleep={config.AUTO_SLEEP_SECONDS}s)")

    if delta > config.AUTO_SLEEP_SECONDS:
        print(f"\n⏰ Inactivité détectée ({config.AUTO_SLEEP_SECONDS}s)")
        enter_sleep_mode(ctx)

def check_deep_sleep(ctx: AppContext) -> None:
    """Vérifie si on doit passer en veille profonde après 10 min de veille."""
    with ctx.sleep_lock:
        # Seulement si en veille simple (pas déjà en profonde)
        if not ctx.is_sleeping or ctx.is_deep_sleeping:
            return

        sleep_duration = time.time() - ctx.sleep_start_time

        # Si en veille depuis plus de 10 minutes
        if sleep_duration > config.DEEP_SLEEP_SECONDS:
            # Sortir du lock avant d'appeler enter_deep_sleep_mode
            pass
        else:
            return

    # Appeler en dehors du lock
    print(f"\n⏰ Veille prolongée détectée ({sleep_duration / 60:.1f} min)")
    enter_deep_sleep_mode(ctx)


def update_speech_timer(ctx: AppContext) -> None:
    ctx.last_speech_time = time.time()


def is_sleeping(ctx: AppContext) -> bool:
    with ctx.sleep_lock:
        return ctx.is_sleeping


def toggle_recording(ctx: AppContext) -> bool:
    """
    Toggle microphone recording on/off.

    Returns:
        bool: New recording state (True = recording, False = paused)
    """
    from api.server import broadcast_recording, broadcast_preview

    new_state = ctx.audio.toggle_recording()

    if new_state:
        print("\n🎤 ENREGISTREMENT ACTIVÉ (F8)")
        broadcast_recording(ctx, True)
        broadcast_preview(ctx, "🎤 Enregistrement actif - Parlez...")
    else:
        print("\n⏸️  ENREGISTREMENT EN PAUSE (F8)")
        broadcast_recording(ctx, False)
        broadcast_preview(ctx, "⏸️ Enregistrement en pause - F8 pour reprendre")
        # Vider la queue audio
        ctx.audio.clear_queue()

    return new_state


def is_recording(ctx: AppContext) -> bool:
    """Check if microphone is currently recording."""
    with ctx.recording_lock:
        return ctx.is_recording


def can_auto_wake(ctx: AppContext) -> bool:
    """
    Check if auto-wake is possible.

    Auto-wake is allowed when:
    - Recording is active (F8 ON)
    - System is sleeping (auto-sleep)
    - Sleep was NOT manual (F9 was not pressed)

    Returns:
        True if auto-wake is possible
    """
    with ctx.recording_lock:
        recording = ctx.is_recording

    with ctx.sleep_lock:
        sleeping = ctx.is_sleeping
        manual = ctx.manual_sleep

    return recording and sleeping and not manual


def auto_wake(ctx: AppContext) -> bool:
    """
    Automatically wake up if conditions are met.

    This is called when voice is detected during auto-sleep.
    Only works if:
    - F8 is ON (recording active)
    - Currently in auto-sleep (not manual F9 sleep)

    Returns:
        True if woke up, False if conditions not met
    """
    from api.server import broadcast_preview, broadcast_state

    # Check conditions atomically
    with ctx.recording_lock:
        recording = ctx.is_recording

    with ctx.sleep_lock:
        if not ctx.is_sleeping:
            return False  # Already awake
        if ctx.manual_sleep:
            return False  # Manual sleep, need F9 to wake
        if not recording:
            return False  # F8 paused, no auto-wake

        # Conditions met - wake up
        was_deep = ctx.is_deep_sleeping
        ctx.is_sleeping = False
        ctx.is_deep_sleeping = False
        ctx.sleep_start_time = 0.0

    ctx.last_speech_time = time.time()

    print("\n🔊 AUTO-RÉVEIL - Voix détectée!")

    if was_deep:
        # Deep sleep recovery (rare case - should reload models)
        from core.models import init_models
        from ui.manager import start_visualizer

        print("   → Rechargement des modèles IA...")
        broadcast_preview(ctx, "⏳ Rechargement modèles IA...")

        try:
            init_models(ctx)
            print("   ✅ Modèles rechargés")
        except Exception as exc:
            print(f"   ❌ Erreur rechargement modèles: {exc}")
            with ctx.sleep_lock:
                ctx.is_sleeping = True
                ctx.is_deep_sleeping = True
            return False

        print("   → Relancement du visualizer...")
        start_visualizer(ctx)
        time.sleep(config.VISUALIZER_START_DELAY)

    broadcast_state(ctx, "active")
    broadcast_preview(ctx, "🔊 Auto-réveil - Parlez!")

    return True


def check_visualizer_closed(ctx: AppContext) -> None:
    if is_sleeping(ctx):
        return

    with ctx.sleep_lock:
        if ctx.manual_sleep:
            return

    with ctx.visualizer_lock:
        if not ctx.visualizer_proc:
            return
        should_sleep = ctx.visualizer_proc.poll() is not None

    if should_sleep:
        print("\n🪟 Visualizer fermé (détection auto)")
        enter_sleep_mode(ctx, manual=False)
