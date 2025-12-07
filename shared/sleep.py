"""Sleep/awake state management - Nouvelle logique F8/F9.

F9 = Système ON/OFF (contrôle principal)
F8 = Micro ON/OFF (seulement si système ON)

Auto-sleep après 30s = équivalent à F9 OFF
Deep sleep après 30min = décharge les modèles
Auto-wake = SUPPRIMÉ

This module uses the ServiceRegistry for decoupled broadcasting
and the EventBus for publishing state change events.

Phase 4 Integration:
- Uses ServiceRegistry for IBroadcaster access
- Publishes events via EventBus for all state transitions
- Error handling decorators for robust state management
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from shared import config
from shared.constants import (
    LOG_PREFIX_ACTIVATE,
    LOG_PREFIX_DEACTIVATE,
    LOG_PREFIX_TOGGLE,
    LOG_PREFIX_AUTOSLEEP,
)
from shared.context import AppContext
from shared.events import EventBus, Events
from shared.interfaces import IBroadcaster
from shared.logger import log_info, log_warn, log_error
from shared.errors import handle_errors
from shared.service_utils import get_broadcaster


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

@handle_errors(log_prefix=LOG_PREFIX_ACTIVATE, reraise=False)
def activate_system(ctx: AppContext) -> None:
    """
    F9 ON: Activate complete system.

    1. Exit sleep mode
    2. Reload models if deep sleep
    3. Start visualizer
    4. Enable recording (F8 ON by default)
    5. Broadcast state "active"
    """
    # Late imports for modules that may have circular dependencies
    from core.models import init_models
    from ui.manager import start_visualizer
    from queue import Empty

    # Get broadcaster from registry
    broadcaster = get_broadcaster()

    # Check if already active
    with ctx.sleep_lock:
        if not ctx.is_sleeping:
            log_info(f"{LOG_PREFIX_ACTIVATE} Déjà actif, skip")
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
        log_info(f"{LOG_PREFIX_ACTIVATE} Queue audio vidée ({cleared_blocks} blocs)")

    log_info(f"{LOG_PREFIX_ACTIVATE} SYSTÈME ACTIVÉ (F9 ON)")

    # Publish activation event
    EventBus.publish(Events.SYSTEM_ACTIVATED)

    if was_deep_sleeping:
        # Reload models from deep sleep
        log_info(f"{LOG_PREFIX_ACTIVATE} Rechargement des modèles IA...")
        if broadcaster:
            broadcaster.send_preview(ctx, "Rechargement modèles IA...")

        try:
            init_models(ctx)
            log_info(f"{LOG_PREFIX_ACTIVATE} Modèles rechargés")
        except Exception as exc:
            log_error(f"{LOG_PREFIX_ACTIVATE} Erreur rechargement: {exc}")
            if broadcaster:
                broadcaster.send_preview(ctx, "Erreur rechargement - Redémarrez")
            # Restore sleep state on error
            with ctx.sleep_lock:
                ctx.is_sleeping = True
                ctx.is_deep_sleeping = True
            return

    # Skip VAD recalibration if already calibrated before
    if ctx.voice_detector is not None:
        ctx.voice_detector.skip_calibration_on_wake()

    # Start visualizer
    log_info(f"{LOG_PREFIX_ACTIVATE} Démarrage visualizer...")
    start_visualizer(ctx)
    time.sleep(config.VISUALIZER_START_DELAY)

    # Enable recording by default
    ctx.audio.set_recording(True)

    # Broadcast states via registry
    if broadcaster:
        broadcaster.send_state(ctx, "active")
        broadcaster.send_recording(ctx, True)
        broadcaster.send_preview(ctx, "Système actif - Parlez maintenant!")

    log_info(f"{LOG_PREFIX_ACTIVATE} Système prêt")


@handle_errors(log_prefix=LOG_PREFIX_DEACTIVATE, reraise=False)
def deactivate_system(ctx: AppContext) -> None:
    """
    F9 OFF: Deactivate complete system.

    1. Force transcription if audio in buffer
    2. Stop recording
    3. Close visualizer
    4. Enter sleep mode
    5. Broadcast state "sleep"
    """
    # Late imports for modules that may have circular dependencies
    from ui.manager import stop_visualizer
    from queue import Empty

    # Get broadcaster from registry
    broadcaster = get_broadcaster()

    # Check if already sleeping
    with ctx.sleep_lock:
        if ctx.is_sleeping:
            log_info(f"{LOG_PREFIX_DEACTIVATE} Déjà en veille, skip")
            return
        # Enter sleep state
        ctx.is_sleeping = True
        ctx.is_deep_sleeping = False
        ctx.sleep_start_time = time.time()
        ctx.manual_sleep = True

    # Reset speech timer to prevent any auto-wake edge cases
    ctx.last_speech_time = 0

    log_info(f"{LOG_PREFIX_DEACTIVATE} SYSTÈME DÉSACTIVÉ (F9 OFF)")

    # Publish deactivation event
    EventBus.publish(Events.SYSTEM_DEACTIVATED)

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
    if broadcaster:
        broadcaster.send_recording(ctx, False)

    # Clear audio queue
    cleared_blocks = 0
    try:
        while True:
            ctx.audio_queue.get_nowait()
            cleared_blocks += 1
    except Empty:
        pass

    if cleared_blocks > 0:
        log_info(f"{LOG_PREFIX_DEACTIVATE} Queue audio vidée ({cleared_blocks} blocs)")

    # Close visualizer
    log_info(f"{LOG_PREFIX_DEACTIVATE} Fermeture visualizer...")
    stop_visualizer(ctx)

    # Broadcast state via registry
    if broadcaster:
        broadcaster.send_state(ctx, "sleep")
        broadcaster.send_preview(ctx, "Mode veille - Appuyez sur F9")

    log_info(f"{LOG_PREFIX_DEACTIVATE} Appuyez sur F9 pour réactiver")
    log_info(f"{LOG_PREFIX_DEACTIVATE} Veille profonde dans {config.DEEP_SLEEP_SECONDS / 60:.0f} minutes...")


def toggle_sleep_mode(ctx: AppContext) -> None:
    """F9: Toggle system ON/OFF."""
    current_time = time.time()
    time_since_toggle = current_time - ctx.last_toggle_time

    if time_since_toggle < config.TOGGLE_COOLDOWN_SECONDS:
        log_info(
            f"{LOG_PREFIX_TOGGLE} Cooldown actif ({time_since_toggle:.2f}s < {config.TOGGLE_COOLDOWN_SECONDS}s) - Ignoré"
        )
        return

    ctx.last_toggle_time = current_time
    log_info(f"{LOG_PREFIX_TOGGLE} F9 pressed at {time.strftime('%H:%M:%S', time.localtime(current_time))}")

    with ctx.sleep_lock:
        sleeping = ctx.is_sleeping

    log_info(f"{LOG_PREFIX_TOGGLE} État: {'VEILLE' if sleeping else 'ACTIF'} -> {'ACTIF' if sleeping else 'VEILLE'}")

    try:
        if sleeping:
            activate_system(ctx)
        else:
            deactivate_system(ctx)
    except Exception as exc:
        log_error(f"{LOG_PREFIX_TOGGLE} Erreur toggle: {exc}")
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
    # Get broadcaster from registry
    broadcaster = get_broadcaster()

    # Check if system is active - F8 ignored when system OFF
    if not is_system_active(ctx):
        log_info("[F8] Système en veille - F8 ignoré")
        return ctx.is_recording

    new_state = ctx.audio.toggle_recording()

    if new_state:
        # F8 ON - Resume recording
        log_info("[F8] MICRO ACTIVÉ (F8 ON)")

        # Publish recording started event
        EventBus.publish(Events.RECORDING_STARTED)

        # Start calibration when resuming from pause
        if ctx.voice_detector is not None:
            ctx.voice_detector.start_calibration()

        if broadcaster:
            broadcaster.send_recording(ctx, True)
            broadcaster.send_preview(ctx, "Calibration en cours...")
    else:
        # F8 OFF - Pause recording + force transcription
        log_info("[F8] MICRO EN PAUSE (F8 OFF)")

        # Publish recording stopped event
        EventBus.publish(Events.RECORDING_STOPPED)

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

        if broadcaster:
            broadcaster.send_recording(ctx, False)
            broadcaster.send_preview(ctx, "Micro en pause - F8 pour reprendre")

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
        log_info(f"{LOG_PREFIX_AUTOSLEEP} Delta: {delta:.1f}s / {config.AUTO_SLEEP_SECONDS:.1f}s")
        check_auto_sleep._last_log = time.time()

    if getattr(config, "DEBUG_AUTO_SLEEP", False):
        log_info(f"{LOG_PREFIX_AUTOSLEEP} [DEBUG] time since last speech: {delta:.2f}s (auto_sleep={config.AUTO_SLEEP_SECONDS}s)")

    if delta > config.AUTO_SLEEP_SECONDS:
        log_info(f"{LOG_PREFIX_AUTOSLEEP} Inactivité détectée ({config.AUTO_SLEEP_SECONDS}s)")
        # Auto-sleep = equivalent to F9 OFF
        deactivate_system(ctx)


# =============================================================================
# Deep Sleep (30min = unload models)
# =============================================================================

def enter_deep_sleep_mode(ctx: AppContext) -> None:
    """Enter deep sleep: unload models."""
    # Late import for modules that may have circular dependencies
    from core.models import unload_models

    with ctx.sleep_lock:
        if ctx.is_deep_sleeping:
            log_info("[Veille Profonde] Déjà en veille profonde, skip")
            return
        if not ctx.is_sleeping:
            log_info("[Veille Profonde] Doit être en veille d'abord")
            return
        ctx.is_deep_sleeping = True

    log_info("VEILLE PROFONDE ACTIVÉE")
    log_info("  Déchargement des modèles IA...")
    log_info("  Appuyez sur F9 pour réactiver (délai: ~3-5s)")

    # Publish deep sleep event
    EventBus.publish(Events.DEEP_SLEEP_ENTERED)

    # Unload models to save memory
    unload_models(ctx)

    log_info("  Veille profonde active - Consommation minimale")


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
    log_info(f"Veille prolongée détectée ({sleep_duration / 60:.1f} min)")
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
        log_info("Visualizer fermé par l'utilisateur")
        # Set sleep state directly (don't call deactivate_system to avoid recursion)
        with ctx.sleep_lock:
            ctx.is_sleeping = True
            ctx.manual_sleep = True
            ctx.sleep_start_time = time.time()
        ctx.audio.set_recording(False)
        log_info("  Système en veille - F9 pour réactiver")
