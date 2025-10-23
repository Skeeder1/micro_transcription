"""Sleep/awake state management."""

from __future__ import annotations

import time

from . import config
from .context import AppContext
from .models import unload_models, init_models
from .state_manager import get_state_manager


def enter_sleep_mode(ctx: AppContext, manual: bool = False) -> None:
    with ctx.sleep_lock:
        if ctx.is_sleeping:
            print("[Veille] Déjà en veille, skip")
            return
        ctx.is_sleeping = True
        ctx.is_deep_sleeping = False
        ctx.sleep_start_time = time.time()
        ctx.manual_sleep = manual

    print("\n💤 Mode VEILLE activé" + (" (manuel)" if manual else " (auto)"))
    print("   Appuyez sur F9 pour réactiver")
    print(f"   Veille profonde dans {config.DEEP_SLEEP_SECONDS / 60:.0f} minutes...")

    # Mettre à jour l'état partagé (visualiseur indépendant)
    state_mgr = get_state_manager()
    state_mgr.update_sleep_state(True)
    state_mgr.update_preview("💤 Mode veille - Appuyez sur F9")


def enter_deep_sleep_mode(ctx: AppContext) -> None:
    """Entre en veille profonde: décharge modèles."""
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
    print("   Appuyez sur F9 pour réactiver (délai: ~3-5s)")

    # Décharger les modèles de RAM
    unload_models(ctx)

    print("   ✅ Veille profonde active - Consommation minimale")


def exit_sleep_mode(ctx: AppContext) -> None:
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

    print("\n🔊 Mode ACTIF - Système réactivé")

    # Mettre à jour l'état partagé
    state_mgr = get_state_manager()

    if was_deep_sleeping:
        # Sortie de veille PROFONDE - recharger modèles
        print("   → Rechargement des modèles IA...")
        state_mgr.update_preview("⏳ Rechargement modèles IA...")

        try:
            init_models(ctx)
            print("   ✅ Modèles rechargés")
        except Exception as exc:
            print(f"   ❌ Erreur rechargement modèles: {exc}")
            state_mgr.update_preview("❌ Erreur rechargement - Redémarrez")
            return

        state_mgr.update_sleep_state(False)
        state_mgr.update_preview("🔊 Système réactivé - Parlez maintenant!")
        print("[Veille Profonde] Réactivation complète (~3-5s)")
    else:
        # Sortie de veille RAPIDE - réactivation instantanée
        state_mgr.update_sleep_state(False)
        state_mgr.update_preview("🔊 Système réactivé - Parlez maintenant!")
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
