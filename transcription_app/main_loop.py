"""Main audio loop with preview and production pipelines."""

from __future__ import annotations

import time
from concurrent.futures import TimeoutError
from queue import Empty

import numpy as np

from . import config
from .audio import detect_activity, paste_via_clipboard
from .audio_preprocessing import preprocess_audio
from .context import AppContext
from .models import transcribe_preview, transcribe_production
from .sleep import check_auto_sleep, check_deep_sleep, check_visualizer_closed, is_sleeping, update_speech_timer
from .sse import broadcast_preview


def run(ctx: AppContext) -> None:
    """Stream microphone audio, manage preview and production outputs."""
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
                if detect_activity(audio_block):
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

            if detect_activity(audio_block):
                preview_buffer.append(audio_block)
                production_buffer.append(audio_block)
                silence_blocks = 0

                update_speech_timer(ctx)

                # Preview temps réel (uniquement si activée)
                if config.ENABLE_PREVIEW:
                    max_preview_blocks = int(config.PREVIEW_WINDOW_SECONDS / config.BLOCK_SECONDS)
                    if len(preview_buffer) > max_preview_blocks:
                        preview_buffer.pop(0)

                    now = time.time()
                    if now - last_preview_update >= config.PREVIEW_UPDATE_INTERVAL:
                        if preview_buffer:
                            preview_audio = np.concatenate(preview_buffer, axis=0)
                            # Apply audio preprocessing (high-pass filter, amplification, normalization)
                            preview_audio = preprocess_audio(preview_audio, sample_rate=config.SAMPLE_RATE)
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
                if silence_blocks >= config.SILENCE_BLOCKS_BEFORE_FLUSH:
                    production_audio = np.concatenate(production_buffer, axis=0)
                    # Apply audio preprocessing for cleaner final transcription
                    production_audio = preprocess_audio(production_audio, sample_rate=config.SAMPLE_RATE)
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                    broadcast_preview(ctx, "")

                    final_text = transcribe_production(ctx, production_audio)
                    if final_text:
                        print(f"📋 {final_text}")
                        paste_via_clipboard(ctx, final_text)

                    preview_buffer.clear()
                    production_buffer.clear()
                    silence_blocks = 0
    except KeyboardInterrupt:
        if config.ENABLE_PRODUCTION and production_buffer:
            print("\r" + " " * 80 + "\r", end="", flush=True)
            production_audio = np.concatenate(production_buffer, axis=0)
            # Apply audio preprocessing on final transcription
            production_audio = preprocess_audio(production_audio, sample_rate=config.SAMPLE_RATE)
            final_text = transcribe_production(ctx, production_audio)
            if final_text:
                print(f"📋 {final_text}")
                paste_via_clipboard(ctx, final_text)
        print("\n👋 Arrêt...")
