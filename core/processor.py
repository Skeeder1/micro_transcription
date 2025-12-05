"""Main audio loop with preview and production pipelines."""

from __future__ import annotations

import time
from concurrent.futures import TimeoutError
from queue import Empty
from typing import Optional

import numpy as np

from shared import config
from shared.context import AppContext
from .audio_capture import detect_activity, paste_via_clipboard
from .audio_preprocessing import preprocess_audio
from .models import transcribe_preview, transcribe_production
from .phrase_detector import PhraseEndDetector


# These imports will be updated once we move sleep and sse modules
# from shared.sleep import check_auto_sleep, check_deep_sleep, check_visualizer_closed, is_sleeping, update_speech_timer
# from api.server import broadcast_preview


def run(ctx: AppContext) -> None:
    """Stream microphone audio, manage preview and production outputs."""
    # Import sleep and API functions here to avoid circular imports
    from shared.sleep import check_auto_sleep, check_deep_sleep, check_visualizer_closed, is_sleeping, update_speech_timer
    from api.server import broadcast_preview

    # Mode visualiseur uniquement - boucle simplifiée
    if not config.ENABLE_TRANSCRIPTION:
        last_sleep_check = time.time()

        print("🎙️ Visualiseur d'ondes actif... (Ctrl+C pour quitter)")
        print("   🌊 Mode visualisation uniquement (transcription désactivée)")
        print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Basculer veille/actif")
        print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s d'inactivité")

        try:
            while True:
                now = time.time()
                if now - last_sleep_check >= 1.0:
                    check_auto_sleep(ctx)
                    check_deep_sleep(ctx)
                    check_visualizer_closed(ctx)
                    last_sleep_check = now

                if is_sleeping(ctx):
                    try:
                        ctx.audio_queue.get(timeout=0.1)
                    except Empty:
                        pass
                    continue

                try:
                    audio_block = ctx.audio_queue.get(timeout=0.1)
                except Empty:
                    continue

                # Vider simplement la queue, l'audio est capturé par le visualiseur
                if detect_activity(audio_block, ctx.voice_detector):
                    update_speech_timer(ctx)
        except KeyboardInterrupt:
            print("\n👋 Arrêt...")
        return

    # Mode transcription complet
    preview_buffer: list[np.ndarray] = []
    production_buffer: list[np.ndarray] = []
    silence_blocks = 0
    last_preview_update = time.time()
    last_sleep_check = time.time()

    # Initialize phrase end detector
    phrase_detector = PhraseEndDetector(
        sample_rate=config.SAMPLE_RATE,
        history_size=getattr(config, 'ENERGY_HISTORY_BLOCKS', 5),
        energy_drop_threshold=getattr(config, 'ENERGY_DROP_THRESHOLD', 0.3),
    )

    # Get max buffer size from config
    max_production_blocks = getattr(config, 'MAX_PRODUCTION_BLOCKS', 60)  # Default 30s

    if config.ENABLE_PREVIEW:
        print("🎙️ Écoute active... (Ctrl+C pour quitter)")
        print("   💬 Preview → Visualiseur (temps réel)")
        print("   📋 Production → Curseur (modèle large)")
        print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Basculer veille/actif")
        print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s d'inactivité")
    else:
        print("🎙️ Transcription directe active... (Ctrl+C pour quitter)")
        print("   📋 Modèle LARGE → Transcription directe au curseur")
        print("   🚫 Pas de prévisualisation (mode performance)")
        print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Basculer veille/actif")
        print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s d'inactivité")

    try:
        while True:
            now = time.time()
            if now - last_sleep_check >= 1.0:
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                check_visualizer_closed(ctx)
                last_sleep_check = now

            if is_sleeping(ctx):
                try:
                    ctx.audio_queue.get(timeout=0.1)
                except Empty:
                    pass
                continue

            try:
                audio_block = ctx.audio_queue.get(timeout=0.1)
            except Empty:
                continue

            is_voice_active = detect_activity(audio_block, ctx.voice_detector)

            # Update phrase detector with current audio
            phrase_detector.update(audio_block, not is_voice_active)

            if is_voice_active:
                preview_buffer.append(audio_block)
                production_buffer.append(audio_block)
                silence_blocks = 0

                update_speech_timer(ctx)

                # Check for buffer overflow (protection against very long speech)
                if len(production_buffer) >= max_production_blocks:
                    print(f"\n⚠️ Buffer limit ({getattr(config, 'MAX_PRODUCTION_SECONDS', 30)}s) - forcing transcription...")
                    production_audio = np.concatenate(production_buffer, axis=0)
                    # Apply full audio preprocessing with noise reduction
                    production_audio = preprocess_audio(production_audio, sample_rate=config.SAMPLE_RATE, for_production=True)
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                    broadcast_preview(ctx, "")

                    final_text = transcribe_production(ctx, production_audio)
                    if final_text:
                        print(f"📋 {final_text}")
                        paste_via_clipboard(ctx, final_text)

                    preview_buffer.clear()
                    production_buffer.clear()
                    phrase_detector.reset()
                    silence_blocks = 0
                    continue

                # Preview temps réel (uniquement si activée)
                if config.ENABLE_PREVIEW:
                    max_preview_blocks = int(config.PREVIEW_WINDOW_SECONDS / config.BLOCK_SECONDS)
                    if len(preview_buffer) > max_preview_blocks:
                        preview_buffer.pop(0)

                    now = time.time()
                    if now - last_preview_update >= config.PREVIEW_UPDATE_INTERVAL:
                        if preview_buffer:
                            preview_audio = np.concatenate(preview_buffer, axis=0)
                            # Apply lighter preprocessing for preview (no noise reduction for speed)
                            preview_audio = preprocess_audio(preview_audio, sample_rate=config.SAMPLE_RATE, for_production=False)
                            future = ctx.executor.submit(transcribe_preview, ctx, preview_audio)
                            try:
                                preview_text = future.result(timeout=config.PREVIEW_TIMEOUT)
                                if preview_text:
                                    broadcast_preview(ctx, preview_text)
                                    print(f"\r💬 {preview_text}", end="", flush=True)
                            except TimeoutError:
                                print("\r⏱️ Preview timeout (skip)", end="", flush=True)
                            except Exception as exc:
                                print(f"\r⚠️ Preview error: {exc}", end="", flush=True)
                        last_preview_update = now
                continue

            # Production (uniquement si activée)
            if config.ENABLE_PRODUCTION and production_buffer:
                silence_blocks += 1

                # Use intelligent phrase end detection
                should_flush = phrase_detector.is_phrase_end(is_silent=True)

                # Fallback to simple silence count if phrase detection disabled
                if not getattr(config, 'ENABLE_PHRASE_DETECTION', True):
                    should_flush = silence_blocks >= config.SILENCE_BLOCKS_BEFORE_FLUSH

                if should_flush:
                    production_audio = np.concatenate(production_buffer, axis=0)
                    # Apply full audio preprocessing with noise reduction
                    production_audio = preprocess_audio(production_audio, sample_rate=config.SAMPLE_RATE, for_production=True)
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                    broadcast_preview(ctx, "")

                    final_text = transcribe_production(ctx, production_audio)
                    if final_text:
                        print(f"📋 {final_text}")
                        paste_via_clipboard(ctx, final_text)

                    preview_buffer.clear()
                    production_buffer.clear()
                    phrase_detector.reset()
                    silence_blocks = 0
    except KeyboardInterrupt:
        if config.ENABLE_PRODUCTION and production_buffer:
            print("\r" + " " * 80 + "\r", end="", flush=True)
            production_audio = np.concatenate(production_buffer, axis=0)
            # Apply full audio preprocessing with noise reduction
            production_audio = preprocess_audio(production_audio, sample_rate=config.SAMPLE_RATE, for_production=True)
            final_text = transcribe_production(ctx, production_audio)
            if final_text:
                print(f"📋 {final_text}")
                paste_via_clipboard(ctx, final_text)
        print("\n👋 Arrêt...")
