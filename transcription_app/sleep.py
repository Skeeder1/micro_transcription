"""Sleep/awake state management."""

from __future__ import annotations

import threading
import time
from typing import Callable

from . import config
from .context import AppContext
from .sse import broadcast_preview
from .visualizer import start_visualizer, stop_visualizer


def enter_sleep_mode(ctx: AppContext, manual: bool = False) -> None:
    with ctx.sleep_lock:
        if ctx.is_sleeping:
            print("[Veille] Déjà en veille, skip")
            return
        ctx.is_sleeping = True
        ctx.manual_sleep = manual

    print("\n💤 Mode VEILLE activé" + (" (manuel)" if manual else " (auto)"))
    print(f"   Appuyez sur {config.HOTKEY_TOGGLE.upper()} pour réactiver")

    stop_visualizer(ctx)
    broadcast_preview(ctx, "")


def exit_sleep_mode(ctx: AppContext) -> None:
    ctx.last_speech_time = time.time()
    ctx.is_reactivating = True

    try:
        with ctx.sleep_lock:
            if not ctx.is_sleeping:
                print("[Veille] Déjà actif, skip")
                ctx.is_reactivating = False
                return
            ctx.is_sleeping = False
            ctx.manual_sleep = False

        print("\n🔊 Mode ACTIF - Système réactivé")
        print("[Veille] Nettoyage préalable...")
        stop_visualizer(ctx)
        time.sleep(0.3)

        start_visualizer(ctx)
        print("[Veille] Attente connexion visualizer...")
        time.sleep(config.VISUALIZER_READY_DELAY)

        broadcast_preview(ctx, "🔊 Système réactivé - Parlez maintenant!")
        print("[Veille] Réactivation complète")

    except Exception as exc:
        print(f"⚠️ Erreur pendant réactivation: {exc}")
        with ctx.sleep_lock:
            ctx.is_sleeping = False
        ctx.is_reactivating = False
        raise

    finally:
        ctx.is_reactivating = False


def toggle_sleep_mode(ctx: AppContext) -> None:
    current_time = time.time()
    time_since_toggle = current_time - ctx.last_toggle_time

    if time_since_toggle < config.TOGGLE_COOLDOWN_SECONDS:
        print(
            f"[Toggle] Cooldown actif ({time_since_toggle:.2f}s < {config.TOGGLE_COOLDOWN_SECONDS}s) - Ignoré"
        )
        return

    ctx.last_toggle_time = current_time

    with ctx.sleep_lock:
        sleeping = ctx.is_sleeping
        reactivating = ctx.is_reactivating

    if reactivating:
        print("[Toggle] Réactivation en cours, veuillez patienter...")
        return

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
    if ctx.is_reactivating:
        return

    with ctx.sleep_lock:
        if ctx.is_sleeping:
            return

    if time.time() - ctx.last_speech_time > config.AUTO_SLEEP_SECONDS:
        print(f"\n⏰ Inactivité détectée ({config.AUTO_SLEEP_SECONDS}s)")
        enter_sleep_mode(ctx)


def update_speech_timer(ctx: AppContext) -> None:
    ctx.last_speech_time = time.time()


def is_sleeping(ctx: AppContext) -> bool:
    with ctx.sleep_lock:
        return ctx.is_sleeping


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
