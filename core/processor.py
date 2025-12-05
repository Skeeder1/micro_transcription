"""
Main audio processing loop.

Orchestrates the audio capture, voice detection, and transcription pipeline
using modular components for better maintainability.
"""

from __future__ import annotations

import time
from queue import Empty
from typing import TYPE_CHECKING

import numpy as np

from shared import config
from .audio_capture import detect_activity, paste_via_clipboard
from .audio_preprocessing import preprocess_audio
from .models import transcribe_preview, transcribe_production
from .phrase_detector import PhraseEndDetector
from .pipeline import AudioBuffer, PreviewManager, ProductionManager

if TYPE_CHECKING:
    from shared.context import AppContext


# =============================================================================
# Main Processing Loop
# =============================================================================

def run(ctx: AppContext) -> None:
    """
    Stream microphone audio, manage preview and production outputs.

    This is the main entry point for the audio processing loop.
    Handles both visualizer-only and full transcription modes.
    """
    # Late imports to avoid circular dependencies
    from shared.sleep import (
        check_auto_sleep, check_deep_sleep, check_visualizer_closed,
        is_sleeping, update_speech_timer
    )
    from api.server import broadcast_preview

    if not config.ENABLE_TRANSCRIPTION:
        _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep,
                            check_visualizer_closed, is_sleeping, update_speech_timer)
    else:
        _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep,
                               check_visualizer_closed, is_sleeping,
                               update_speech_timer, broadcast_preview)


# =============================================================================
# Visualizer-Only Mode
# =============================================================================

def _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep,
                         check_visualizer_closed, is_sleeping, update_speech_timer):
    """
    Run in visualizer-only mode (no transcription).

    Simply captures audio for visualization and manages sleep state.
    """
    _print_visualizer_banner()
    last_sleep_check = time.time()

    try:
        while True:
            # Throttled sleep checks
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                check_visualizer_closed(ctx)
                last_sleep_check = time.time()

            # Skip processing when sleeping
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                continue

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                continue

            # Update speech timer on voice activity
            if detect_activity(audio_block, ctx.voice_detector):
                update_speech_timer(ctx)

    except KeyboardInterrupt:
        print("\n👋 Arrêt...")


# =============================================================================
# Full Transcription Mode
# =============================================================================

def _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep,
                           check_visualizer_closed, is_sleeping,
                           update_speech_timer, broadcast_preview):
    """
    Run full transcription mode with preview and production pipelines.

    Uses modular components for buffer management, preview timing,
    and production decisions.
    """
    # Initialize components
    buffer = AudioBuffer(
        max_production_seconds=getattr(config, 'MAX_PRODUCTION_SECONDS', 30.0),
        preview_window_seconds=config.PREVIEW_WINDOW_SECONDS,
        block_seconds=config.BLOCK_SECONDS,
    )

    phrase_detector = PhraseEndDetector(
        sample_rate=config.SAMPLE_RATE,
        history_size=getattr(config, 'ENERGY_HISTORY_BLOCKS', 5),
        energy_drop_threshold=getattr(config, 'ENERGY_DROP_THRESHOLD', 0.3),
    )

    preview_manager = PreviewManager(
        update_interval=config.PREVIEW_UPDATE_INTERVAL,
        timeout=config.PREVIEW_TIMEOUT,
    )

    production_manager = ProductionManager()

    _print_transcription_banner()
    last_sleep_check = time.time()

    try:
        while True:
            # Throttled sleep checks
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                check_visualizer_closed(ctx)
                last_sleep_check = time.time()

            # Skip processing when sleeping
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                continue

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                continue

            # Detect voice activity
            is_voice = detect_activity(audio_block, ctx.voice_detector)
            phrase_detector.update(audio_block, not is_voice)

            if is_voice:
                _handle_voice_activity(
                    ctx, audio_block, buffer, phrase_detector,
                    preview_manager, update_speech_timer, broadcast_preview
                )
            else:
                _handle_silence(
                    ctx, buffer, phrase_detector, production_manager,
                    broadcast_preview
                )

    except KeyboardInterrupt:
        _handle_shutdown(ctx, buffer, broadcast_preview)


# =============================================================================
# Voice Activity Handling
# =============================================================================

def _handle_voice_activity(ctx, audio_block, buffer, phrase_detector,
                           preview_manager, update_speech_timer, broadcast_preview):
    """Handle audio block when voice is detected."""
    buffer.add_voice_audio(audio_block)
    update_speech_timer(ctx)

    # Check for buffer overflow
    if buffer.is_production_overflow:
        _flush_production_overflow(ctx, buffer, phrase_detector, broadcast_preview)
        return

    # Update preview if enabled
    if config.ENABLE_PREVIEW and preview_manager.should_update():
        _update_preview(ctx, buffer, preview_manager, broadcast_preview)


def _flush_production_overflow(ctx, buffer, phrase_detector, broadcast_preview):
    """Handle production buffer overflow."""
    print(f"\n⚠️ Buffer limit ({getattr(config, 'MAX_PRODUCTION_SECONDS', 30)}s) - forcing transcription...")

    audio = buffer.get_production_audio()
    if audio is not None:
        audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)

        print("\r" + " " * 80 + "\r", end="", flush=True)
        broadcast_preview(ctx, "")

        final_text = transcribe_production(ctx, audio)
        if final_text:
            print(f"📋 {final_text}")
            paste_via_clipboard(ctx, final_text)

    buffer.clear()
    phrase_detector.reset()


def _update_preview(ctx, buffer, preview_manager, broadcast_preview):
    """Update preview transcription."""
    audio = buffer.get_preview_audio()
    if audio is None:
        return

    audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=False)
    preview_text = preview_manager.execute_preview(
        ctx, audio, transcribe_preview, broadcast_preview
    )

    if preview_text:
        print(f"\r💬 {preview_text}", end="", flush=True)


# =============================================================================
# Silence Handling
# =============================================================================

def _handle_silence(ctx, buffer, phrase_detector, production_manager, broadcast_preview):
    """Handle audio block when silence is detected."""
    if not config.ENABLE_PRODUCTION or not buffer.has_production_audio:
        return

    buffer.add_silence()

    # Check if we should flush production
    should_flush = production_manager.should_flush(buffer, phrase_detector, is_silent=True)

    if should_flush:
        _flush_production(ctx, buffer, phrase_detector, broadcast_preview)


def _flush_production(ctx, buffer, phrase_detector, broadcast_preview):
    """Flush production buffer and transcribe."""
    audio = buffer.get_production_audio()
    if audio is None:
        return

    audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)

    print("\r" + " " * 80 + "\r", end="", flush=True)
    broadcast_preview(ctx, "")

    final_text = transcribe_production(ctx, audio)
    if final_text:
        print(f"📋 {final_text}")
        paste_via_clipboard(ctx, final_text)

    buffer.clear()
    phrase_detector.reset()


# =============================================================================
# Utility Functions
# =============================================================================

def _should_check_sleep(last_check: float, interval: float = 1.0) -> bool:
    """Check if enough time has passed for sleep checks."""
    return time.time() - last_check >= interval


def _drain_audio_queue(ctx) -> None:
    """Drain audio queue when sleeping (discard audio)."""
    try:
        ctx.audio_queue.get(timeout=0.1)
    except Empty:
        pass


def _get_audio_block(ctx):
    """Get next audio block from queue."""
    try:
        return ctx.audio_queue.get(timeout=0.1)
    except Empty:
        return None


def _handle_shutdown(ctx, buffer, broadcast_preview):
    """Handle graceful shutdown with pending audio."""
    if config.ENABLE_PRODUCTION and buffer.has_production_audio:
        print("\r" + " " * 80 + "\r", end="", flush=True)

        audio = buffer.get_production_audio()
        if audio is not None:
            audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)
            final_text = transcribe_production(ctx, audio)
            if final_text:
                print(f"📋 {final_text}")
                paste_via_clipboard(ctx, final_text)

    print("\n👋 Arrêt...")


# =============================================================================
# Banner Messages
# =============================================================================

def _print_visualizer_banner():
    """Print startup banner for visualizer-only mode."""
    print("🎙️ Visualiseur d'ondes actif... (Ctrl+C pour quitter)")
    print("   🌊 Mode visualisation uniquement (transcription désactivée)")
    print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Basculer veille/actif")
    print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s d'inactivité")


def _print_transcription_banner():
    """Print startup banner for transcription mode."""
    if config.ENABLE_PREVIEW:
        print("🎙️ Écoute active... (Ctrl+C pour quitter)")
        print("   💬 Preview → Visualiseur (temps réel)")
        print("   📋 Production → Curseur (modèle large)")
    else:
        print("🎙️ Transcription directe active... (Ctrl+C pour quitter)")
        print("   📋 Modèle LARGE → Transcription directe au curseur")
        print("   🚫 Pas de prévisualisation (mode performance)")

    print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Basculer veille/actif")
    print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s d'inactivité")
