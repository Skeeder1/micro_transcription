"""Sleep/awake state management - Nouvelle logique F8/F9.

F9 = Système ON/OFF (contrôle principal)
F8 = Micro ON/OFF (seulement si système ON)

Auto-sleep après 30s = équivalent à F9 OFF
Deep sleep après 30min = décharge les modèles
Auto-wake = SUPPRIMÉ
"""

from __future__ import annotations

import time

from shared import config
from shared.context import AppContext


# =============================================================================
# System State Helpers
# =============================================================================

def is_system_active(ctx: AppContext) -> bool:
    """Check if system is active (not sleeping)."""
    with ctx.sleep_lock:
        return not ctx.is_sleeping


def is_sleeping(ctx: AppContext) -> bool:
    """Check if system is sleeping."""
    with ctx.sleep_lock:
        return ctx.is_sleeping


def is_recording(ctx: AppContext) -> bool:
    """Check if microphone is currently recording."""
    with ctx.recording_lock:
        return ctx.is_recording


# =============================================================================
# F9 - System ON/OFF Control
# =============================================================================

def activate_system(ctx: AppContext) -> None:
    """
    F9 ON: Activate complete system.

    1. Exit sleep mode
    2. Reload models if deep sleep
    3. Start visualizer
    4. Enable recording (F8 ON by default)
    5. Broadcast state "active"
    """
    from core.models import init_models
    from api.server import broadcast_preview, broadcast_state, broadcast_recording
    from ui.manager import start_visualizer
    from queue import Empty

    # Check if already active
    with ctx.sleep_lock:
        if not ctx.is_sleeping:
            print("[Activate] Déjà actif, skip")
            return
        was_deep_sleeping = ctx.is_deep_sleeping
        # Exit sleep state
        ctx.is_sleeping = False
        ctx.is_deep_sleeping = False
        ctx.sleep_start_time = 0.0
        ctx.manual_sleep = False

    # Reset speech timer
    ctx.last_speech_time = time.time()

    # Clear audio queue
    cleared_blocks = 0
    try:
        while True:
            ctx.audio_queue.get_nowait()
            cleared_blocks += 1
    except Empty:
        pass

    if cleared_blocks > 0:
        print(f"[Activate] Queue audio vidée ({cleared_blocks} blocs)")

    print("\n🔊 SYSTÈME ACTIVÉ (F9 ON)")

    if was_deep_sleeping:
        # Reload models from deep sleep
        print("   → Rechargement des modèles IA...")
        broadcast_preview(ctx, "⏳ Rechargement modèles IA...")

        try:
            init_models(ctx)
            print("   ✅ Modèles rechargés")
        except Exception as exc:
            print(f"   ❌ Erreur rechargement: {exc}")
            broadcast_preview(ctx, "❌ Erreur rechargement - Redémarrez")
            # Restore sleep state on error
            with ctx.sleep_lock:
                ctx.is_sleeping = True
                ctx.is_deep_sleeping = True
            return

    # Skip VAD recalibration if already calibrated before
    if ctx.voice_detector is not None:
        ctx.voice_detector.skip_calibration_on_wake()

    # Start visualizer
    print("   → Démarrage visualizer...")
    start_visualizer(ctx)
    time.sleep(config.VISUALIZER_START_DELAY)

    # Enable recording by default
    ctx.audio.set_recording(True)

    # Broadcast states
    broadcast_state(ctx, "active")
    broadcast_recording(ctx, True)
    broadcast_preview(ctx, "🔊 Système actif - Parlez maintenant!")

    print("   ✅ Système prêt - Parlez!")


def deactivate_system(ctx: AppContext) -> None:
    """
    F9 OFF: Deactivate complete system.

    1. Force transcription if audio in buffer
    2. Stop recording
    3. Close visualizer
    4. Enter sleep mode
    5. Broadcast state "sleep"
    """
    from api.server import broadcast_preview, broadcast_state, broadcast_recording
    from ui.manager import stop_visualizer
    from queue import Empty

    # Check if already sleeping
    with ctx.sleep_lock:
        if ctx.is_sleeping:
            print("[Deactivate] Déjà en veille, skip")
            return
        # Enter sleep state
        ctx.is_sleeping = True
        ctx.is_deep_sleeping = False
        ctx.sleep_start_time = time.time()
        ctx.manual_sleep = True

    # Reset speech timer to prevent any auto-wake edge cases
    ctx.last_speech_time = 0

    print("\n💤 SYSTÈME DÉSACTIVÉ (F9 OFF)")

    # Signal force flush to processor (transcribe what's in buffer)
    ctx.force_flush = True

    # Give processor time to flush (check every 50ms, max 1s)
    for _ in range(20):
        if not ctx.force_flush:
            break
        time.sleep(0.05)

    # Reset flag in case processor didn't clear it
    ctx.force_flush = False

    # Disable recording
    ctx.audio.set_recording(False)
    broadcast_recording(ctx, False)

    # Clear audio queue
    cleared_blocks = 0
    try:
        while True:
            ctx.audio_queue.get_nowait()
            cleared_blocks += 1
    except Empty:
        pass

    if cleared_blocks > 0:
        print(f"   Queue audio vidée ({cleared_blocks} blocs)")

    # Close visualizer
    print("   → Fermeture visualizer...")
    stop_visualizer(ctx)

    # Broadcast state
    broadcast_state(ctx, "sleep")
    broadcast_preview(ctx, "💤 Mode veille - Appuyez sur F9")

    print("   Appuyez sur F9 pour réactiver")
    print(f"   Veille profonde dans {config.DEEP_SLEEP_SECONDS / 60:.0f} minutes...")


def toggle_sleep_mode(ctx: AppContext) -> None:
    """F9: Toggle system ON/OFF."""
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

    print(f"[Toggle] État: {'VEILLE' if sleeping else 'ACTIF'} → {'ACTIF' if sleeping else 'VEILLE'}")

    try:
        if sleeping:
            activate_system(ctx)
        else:
            deactivate_system(ctx)
    except Exception as exc:
        print(f"❌ Erreur toggle: {exc}")
        ctx.last_toggle_time = 0.0


# =============================================================================
# F8 - Microphone ON/OFF Control
# =============================================================================

def toggle_recording(ctx: AppContext) -> bool:
    """
    F8: Toggle microphone recording (only if system is active).

    When turning OFF:
    - Forces transcription of buffered audio
    - Clears audio queue

    Returns:
        bool: New recording state (True = recording, False = paused)
        Returns current state if system is OFF (no toggle)
    """
    from api.server import broadcast_recording, broadcast_preview

    # Check if system is active - F8 ignored when system OFF
    if not is_system_active(ctx):
        print("[F8] Système en veille - F8 ignoré")
        return ctx.is_recording

    new_state = ctx.audio.toggle_recording()

    if new_state:
        # F8 ON - Resume recording
        print("\n🎤 MICRO ACTIVÉ (F8 ON)")

        # Start calibration when resuming from pause
        if ctx.voice_detector is not None:
            ctx.voice_detector.start_calibration()

        broadcast_recording(ctx, True)
        broadcast_preview(ctx, "🎯 Calibration en cours...")
    else:
        # F8 OFF - Pause recording + force transcription
        print("\n⏸️ MICRO EN PAUSE (F8 OFF)")

        # Signal force flush to processor
        ctx.force_flush = True

        # Give processor time to flush (check every 50ms, max 1s)
        for _ in range(20):
            if not ctx.force_flush:
                break
            time.sleep(0.05)

        # Reset flag in case processor didn't clear it
        ctx.force_flush = False

        # Clear audio queue
        ctx.audio.clear_queue()

        broadcast_recording(ctx, False)
        broadcast_preview(ctx, "⏸️ Micro en pause - F8 pour reprendre")

    return new_state


# =============================================================================
# Auto-Sleep (30s inactivity = F9 OFF)
# =============================================================================

def check_auto_sleep(ctx: AppContext) -> None:
    """
    Auto-sleep after 30s of inactivity.

    Equivalent to F9 OFF - closes visualizer and enters sleep.
    """
    with ctx.sleep_lock:
        if ctx.is_sleeping:
            return

    delta = time.time() - ctx.last_speech_time

    # Throttled logging every 5 seconds
    if not hasattr(check_auto_sleep, '_last_log'):
        check_auto_sleep._last_log = 0.0

    if time.time() - check_auto_sleep._last_log > 5.0:
        print(f"[AutoSleep] Delta: {delta:.1f}s / {config.AUTO_SLEEP_SECONDS:.1f}s")
        check_auto_sleep._last_log = time.time()

    if getattr(config, "DEBUG_AUTO_SLEEP", False):
        print(f"[DEBUG] time since last speech: {delta:.2f}s (auto_sleep={config.AUTO_SLEEP_SECONDS}s)")

    if delta > config.AUTO_SLEEP_SECONDS:
        print(f"\n⏰ Inactivité détectée ({config.AUTO_SLEEP_SECONDS}s)")
        # Auto-sleep = equivalent to F9 OFF
        deactivate_system(ctx)


# =============================================================================
# Deep Sleep (30min = unload models)
# =============================================================================

def enter_deep_sleep_mode(ctx: AppContext) -> None:
    """Enter deep sleep: unload models."""
    from core.models import unload_models

    with ctx.sleep_lock:
        if ctx.is_deep_sleeping:
            print("[Veille Profonde] Déjà en veille profonde, skip")
            return
        if not ctx.is_sleeping:
            print("[Veille Profonde] Doit être en veille d'abord")
            return
        ctx.is_deep_sleeping = True

    print("\n🌙 VEILLE PROFONDE ACTIVÉE")
    print("   → Déchargement des modèles IA...")
    print("   Appuyez sur F9 pour réactiver (délai: ~3-5s)")

    # Unload models to save memory
    unload_models(ctx)

    print("   ✅ Veille profonde active - Consommation minimale")


def check_deep_sleep(ctx: AppContext) -> None:
    """Check if should enter deep sleep after 30min of sleep."""
    with ctx.sleep_lock:
        # Only if in sleep mode (not already deep)
        if not ctx.is_sleeping or ctx.is_deep_sleeping:
            return

        sleep_duration = time.time() - ctx.sleep_start_time

        if sleep_duration > config.DEEP_SLEEP_SECONDS:
            # Exit lock before calling enter_deep_sleep_mode
            pass
        else:
            return

    # Call outside lock
    print(f"\n⏰ Veille prolongée détectée ({sleep_duration / 60:.1f} min)")
    enter_deep_sleep_mode(ctx)


# =============================================================================
# Utility Functions
# =============================================================================

def update_speech_timer(ctx: AppContext) -> None:
    """Update last speech time to now."""
    ctx.last_speech_time = time.time()


def check_visualizer_closed(ctx: AppContext) -> None:
    """
    Check if visualizer was closed by user.

    If closed while system is active, enter sleep mode.
    """
    if is_sleeping(ctx):
        return

    with ctx.visualizer_lock:
        if not ctx.visualizer_proc:
            return
        visualizer_closed = ctx.visualizer_proc.poll() is not None

    if visualizer_closed:
        print("\n🪟 Visualizer fermé par l'utilisateur")
        # Set sleep state directly (don't call deactivate_system to avoid recursion)
        with ctx.sleep_lock:
            ctx.is_sleeping = True
            ctx.manual_sleep = True
            ctx.sleep_start_time = time.time()
        ctx.audio.set_recording(False)
        print("   → Système en veille - F9 pour réactiver")
