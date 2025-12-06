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
    from api.server import broadcast_preview, broadcast_vad, broadcast_processing

    if not config.ENABLE_TRANSCRIPTION:
        _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep,
                            check_visualizer_closed, is_sleeping, update_speech_timer,
                            broadcast_vad)
    else:
        _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep,
                               check_visualizer_closed, is_sleeping,
                               update_speech_timer, broadcast_preview,
                               broadcast_vad, broadcast_processing)


# =============================================================================
# Visualizer-Only Mode
# =============================================================================

def _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep,
                         check_visualizer_closed, is_sleeping, update_speech_timer,
                         broadcast_vad):
    """
    Run in visualizer-only mode (no transcription).

    Simply captures audio for visualization and manages sleep state.
    Auto-wake is DISABLED - only F9 can wake from sleep.
    """
    _print_visualizer_banner()
    last_sleep_check = time.time()
    was_voice = False  # Track VAD state transitions

    try:
        while True:
            # Throttled sleep checks
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                check_visualizer_closed(ctx)
                last_sleep_check = time.time()

            # Handle sleep state - NO auto-wake, just drain queue
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                continue

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                continue

            # Detect voice and broadcast VAD state changes
            is_voice = detect_activity(audio_block, ctx.voice_detector)
            if is_voice != was_voice:
                broadcast_vad(ctx, is_voice)
                was_voice = is_voice

            # Update speech timer on voice activity
            if is_voice:
                update_speech_timer(ctx)

    except KeyboardInterrupt:
        print("\n👋 Arrêt...")


# =============================================================================
# Full Transcription Mode
# =============================================================================

def _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep,
                           check_visualizer_closed, is_sleeping,
                           update_speech_timer, broadcast_preview,
                           broadcast_vad, broadcast_processing):
    """
    Run full transcription mode with preview and production pipelines.

    Uses modular components for buffer management, preview timing,
    and production decisions.

    Auto-wake is DISABLED - only F9 can wake from sleep.
    Supports force_flush flag for F8 OFF and F9 OFF transcription.
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
    was_voice = False  # Track VAD state transitions

    # Diagnostic counters
    diag_voice_count = 0
    diag_silence_count = 0
    diag_last_report = time.time()
    DIAG_INTERVAL = 5.0  # Report every 5 seconds

    try:
        while True:
            # Check force_flush flag (set by F8 OFF or F9 OFF)
            if ctx.force_flush:
                _force_flush_buffer(ctx, buffer, phrase_detector,
                                   broadcast_preview, broadcast_processing)
                ctx.force_flush = False  # Clear flag

            # Throttled sleep checks
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                check_visualizer_closed(ctx)
                last_sleep_check = time.time()

            # Handle sleep state - NO auto-wake, just drain queue
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                continue

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                continue

            # Detect voice activity and broadcast VAD state changes
            is_voice = detect_activity(audio_block, ctx.voice_detector)
            if is_voice != was_voice:
                broadcast_vad(ctx, is_voice)
                was_voice = is_voice

            phrase_detector.update(audio_block, not is_voice)

            # Diagnostic: count voice/silence ratio
            if is_voice:
                diag_voice_count += 1
            else:
                diag_silence_count += 1

            # Periodic diagnostic report
            now = time.time()
            if now - diag_last_report >= DIAG_INTERVAL:
                total = diag_voice_count + diag_silence_count
                voice_pct = (diag_voice_count / total * 100) if total > 0 else 0
                delta_speech = now - ctx.last_speech_time
                print(f"\n[DIAG] Voix: {diag_voice_count} ({voice_pct:.0f}%) | "
                      f"Silence: {diag_silence_count} | "
                      f"Buffer: {len(buffer._production)} blocks | "
                      f"Depuis parole: {delta_speech:.1f}s", flush=True)
                diag_voice_count = 0
                diag_silence_count = 0
                diag_last_report = now

            if is_voice:
                _handle_voice_activity(
                    ctx, audio_block, buffer, phrase_detector,
                    preview_manager, update_speech_timer, broadcast_preview,
                    broadcast_processing
                )
            else:
                _handle_silence(
                    ctx, buffer, phrase_detector, production_manager,
                    broadcast_preview, broadcast_processing
                )

    except KeyboardInterrupt:
        _handle_shutdown(ctx, buffer, broadcast_preview, broadcast_processing)


# =============================================================================
# Voice Activity Handling
# =============================================================================

def _handle_voice_activity(ctx, audio_block, buffer, phrase_detector,
                           preview_manager, update_speech_timer, broadcast_preview,
                           broadcast_processing):
    """Handle audio block when voice is detected."""
    buffer.add_voice_audio(audio_block)
    update_speech_timer(ctx)

    # Check for buffer overflow
    if buffer.is_production_overflow:
        _flush_production_overflow(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing)
        return

    # Update preview if enabled
    if config.ENABLE_PREVIEW and preview_manager.should_update():
        _update_preview(ctx, buffer, preview_manager, broadcast_preview)


def _flush_production_overflow(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing):
    """Handle production buffer overflow."""
    print(f"\n⚠️ Buffer limit ({getattr(config, 'MAX_PRODUCTION_SECONDS', 30)}s) - forcing transcription...")

    audio = buffer.get_production_audio()
    if audio is not None:
        broadcast_processing(ctx, True)  # Signal start
        audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)

        print("\r" + " " * 80 + "\r", end="", flush=True)
        broadcast_preview(ctx, "⏳ Transcription...")

        final_text = transcribe_production(ctx, audio)
        broadcast_processing(ctx, False)  # Signal done

        if final_text:
            print(f"📋 {final_text}")
            paste_via_clipboard(ctx, final_text)
            broadcast_preview(ctx, f"✅ {final_text}")
        else:
            broadcast_preview(ctx, "")

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

def _handle_silence(ctx, buffer, phrase_detector, production_manager, broadcast_preview, broadcast_processing):
    """Handle audio block when silence is detected."""
    if not config.ENABLE_PRODUCTION or not buffer.has_production_audio:
        return

    buffer.add_silence()

    # Check if we should flush production
    should_flush = production_manager.should_flush(buffer, phrase_detector, is_silent=True)

    if should_flush:
        _flush_production(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing)


def _flush_production(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing):
    """Flush production buffer and transcribe."""
    audio = buffer.get_production_audio()
    if audio is None:
        return

    broadcast_processing(ctx, True)  # Signal start
    audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)

    print("\r" + " " * 80 + "\r", end="", flush=True)
    broadcast_preview(ctx, "⏳ Transcription...")

    final_text = transcribe_production(ctx, audio)
    broadcast_processing(ctx, False)  # Signal done

    if final_text:
        print(f"📋 {final_text}")
        paste_via_clipboard(ctx, final_text)
        broadcast_preview(ctx, f"✅ {final_text}")
    else:
        broadcast_preview(ctx, "")

    buffer.clear()
    phrase_detector.reset()


def _force_flush_buffer(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing):
    """
    Force immediate transcription of buffered audio.

    Called when F8 OFF or F9 OFF is pressed to transcribe
    whatever audio is currently in the buffer.
    """
    if not buffer.has_production_audio:
        print("[ForceFlush] Pas d'audio en buffer, skip")
        return

    print("\n⚡ TRANSCRIPTION FORCÉE (F8/F9 OFF)")

    audio = buffer.get_production_audio()
    if audio is None:
        return

    broadcast_processing(ctx, True)  # Signal start
    audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)

    broadcast_preview(ctx, "⏳ Transcription forcée...")

    final_text = transcribe_production(ctx, audio)
    broadcast_processing(ctx, False)  # Signal done

    if final_text:
        print(f"   📋 {final_text}")
        paste_via_clipboard(ctx, final_text)
        broadcast_preview(ctx, f"✅ {final_text}")
    else:
        print("   (pas de texte détecté)")
        broadcast_preview(ctx, "")

    buffer.clear()
    phrase_detector.reset()
    print("   ✅ Buffer vidé")


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


def _handle_shutdown(ctx, buffer, broadcast_preview, broadcast_processing):
    """Handle graceful shutdown with pending audio."""
    if config.ENABLE_PRODUCTION and buffer.has_production_audio:
        print("\r" + " " * 80 + "\r", end="", flush=True)

        audio = buffer.get_production_audio()
        if audio is not None:
            broadcast_processing(ctx, True)  # Signal start
            audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)
            final_text = transcribe_production(ctx, audio)
            broadcast_processing(ctx, False)  # Signal done
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
    print("   🎤 F8 → Pause/Reprendre micro (seulement si système actif)")
    print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Système ON/OFF (ouvre/ferme UI)")
    print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s = F9 OFF")


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

    print("   🎤 F8 → Pause/Reprendre micro (force transcription si OFF)")
    print(f"   💤 {config.HOTKEY_TOGGLE.upper()} → Système ON/OFF (ouvre/ferme UI)")
    print(f"   ⏰ Veille auto après {config.AUTO_SLEEP_SECONDS}s = F9 OFF")
