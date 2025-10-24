"""Sleep/awake state management."""

from __future__ import annotations

import time

from shared import config
from shared.context import AppContext


def enter_sleep_mode(ctx: AppContext, manual: bool = False) -> None:
    # Import here to avoid circular imports
    from api.server import broadcast_preview, broadcast_state

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
