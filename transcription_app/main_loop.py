"""Main audio loop with preview and production pipelines."""

from __future__ import annotations

import time
from concurrent.futures import TimeoutError
from queue import Empty

import numpy as np

from . import config
from .audio import detect_activity, paste_via_clipboard
from .context import AppContext
from .models import transcribe_preview, transcribe_production
from .sleep import check_auto_sleep, check_visualizer_closed, is_sleeping, update_speech_timer
from .sse import broadcast_preview


def run(ctx: AppContext) -> None:
    """Stream microphone audio, manage preview and production outputs."""
    preview_buffer: list[np.ndarray] = []
    production_buffer: list[np.ndarray] = []
    silence_blocks = 0
    last_preview_update = time.time()
    last_sleep_check = time.time()

    print("🎙️ Écoute active... (Ctrl+C pour quitter)")
    print("   💬 Preview → Visualizer (temps réel)")
    print("   📋 Production → Presse-papiers (haute qualité)")
    print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Basculer veille/actif")
    print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s d'inactivité")

    try:
        while True:
            now = time.time()
            if now - last_sleep_check >= 1.0:
                check_auto_sleep(ctx)
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

                max_preview_blocks = int(config.PREVIEW_WINDOW_SECONDS / config.BLOCK_SECONDS)
                if len(preview_buffer) > max_preview_blocks:
                    preview_buffer.pop(0)

                now = time.time()
                if now - last_preview_update >= config.PREVIEW_UPDATE_INTERVAL:
                    if preview_buffer:
                        preview_audio = np.concatenate(preview_buffer, axis=0)
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

            if production_buffer:
                silence_blocks += 1
                if silence_blocks >= config.SILENCE_BLOCKS_BEFORE_FLUSH:
                    production_audio = np.concatenate(production_buffer, axis=0)
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
        if production_buffer:
            print("\r" + " " * 80 + "\r", end="", flush=True)
            production_audio = np.concatenate(production_buffer, axis=0)
            final_text = transcribe_production(ctx, production_audio)
            if final_text:
                print(f"📋 {final_text}")
                paste_via_clipboard(ctx, final_text)
        print("\n👋 Arrêt...")
