"""
Main audio processing loop - Nouvelle logique F8/F9.

Architecture:
- Le système démarre ACTIF (F9 pour mettre en veille)
- Quand actif: VAD détecte la voix, accumule l'audio
- Transcription auto après 1-2s de silence
- F8 force la transcription immédiate

États:
- Système OFF (veille): drain queue, attendre F9
- Système ON + Micro OFF: drain queue, attendre F8
- Système ON + Micro ON: traitement audio actif
"""

from __future__ import annotations

import time
from queue import Empty
from typing import TYPE_CHECKING

import numpy as np

from shared import config
from .audio_capture import detect_activity, paste_via_clipboard, compute_waveform_metrics
from .audio_preprocessing import preprocess_audio
from .models import transcribe_preview, transcribe_production
from .phrase_detector import PhraseEndDetector
from .pipeline import AudioBuffer, PreviewManager, ProductionManager

if TYPE_CHECKING:
    from shared.context import AppContext


# =============================================================================
# Waveform Configuration
# =============================================================================

# Number of subdivisions per audio block for smooth waveform
# With BLOCK_SECONDS=0.5, this gives 0.5/20 = 25ms per sample = 40 Hz
WAVEFORM_SUBDIVISIONS = 20


def _broadcast_waveform_subdivided(ctx, audio_block, is_voice, broadcast_waveform) -> None:
    """
    Broadcast multiple waveform samples per audio block for fluid animation.

    Instead of sending 1 sample per 0.5s block (2 Hz), we subdivide
    each block into WAVEFORM_SUBDIVISIONS samples (~40 Hz).
    """
    flat_audio = audio_block.flatten()
    total_samples = len(flat_audio)
    samples_per_sub = total_samples // WAVEFORM_SUBDIVISIONS

    if samples_per_sub < 10:
        # Block too small to subdivide, send as single sample
        rms, peak = compute_waveform_metrics(audio_block)
        broadcast_waveform(ctx, rms, peak, is_voice)
        return

    for i in range(WAVEFORM_SUBDIVISIONS):
        start = i * samples_per_sub
        end = start + samples_per_sub
        sub_block = flat_audio[start:end]

        rms, peak = compute_waveform_metrics(sub_block)
        broadcast_waveform(ctx, rms, peak, is_voice)


# =============================================================================
# Main Processing Loop
# =============================================================================

def run(ctx: AppContext) -> None:
    """
    Stream microphone audio, manage preview and production outputs.

    Le système démarre ACTIF. L'utilisateur peut appuyer sur F9 pour mettre en veille.
    """
    from shared.sleep import (
        check_auto_sleep, check_deep_sleep, is_sleeping, update_speech_timer
    )
    from api.server import broadcast_preview, broadcast_vad, broadcast_processing, broadcast_waveform

    if not config.ENABLE_TRANSCRIPTION:
        _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep, is_sleeping,
                            update_speech_timer, broadcast_waveform)
    else:
        _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep, is_sleeping,
                               update_speech_timer, broadcast_preview, broadcast_vad,
                               broadcast_processing, broadcast_waveform)


# =============================================================================
# Visualizer-Only Mode
# =============================================================================

def _run_visualizer_only(ctx, check_auto_sleep, check_deep_sleep, is_sleeping,
                         update_speech_timer, broadcast_waveform):
    """
    Run in visualizer-only mode (no transcription).
    """
    _print_startup_banner()
    last_sleep_check = time.time()

    try:
        while True:
            # Vérifications périodiques
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                last_sleep_check = time.time()

            # Si système en veille, drain et attendre
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                continue

            # Si micro désactivé, drain et attendre
            if not ctx.is_recording:
                _drain_audio_queue(ctx)
                continue

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                continue

            # Detect voice activity
            is_voice = detect_activity(audio_block, ctx.voice_detector)

            # Broadcast subdivided waveform data (40 Hz for fluid animation)
            _broadcast_waveform_subdivided(ctx, audio_block, is_voice, broadcast_waveform)

            # Update speech timer on voice activity
            if is_voice:
                update_speech_timer(ctx)

    except KeyboardInterrupt:
        print("\n👋 Arrêt...")


# =============================================================================
# Full Transcription Mode
# =============================================================================

def _run_full_transcription(ctx, check_auto_sleep, check_deep_sleep, is_sleeping,
                           update_speech_timer, broadcast_preview, broadcast_vad,
                           broadcast_processing, broadcast_waveform):
    """
    Run full transcription mode with preview and production pipelines.

    Nouvelle logique:
    - Transcription après SILENCE_BEFORE_TRANSCRIBE_SECONDS de silence
    - Force flush via flag ctx.force_flush (quand F8 désactive le micro)
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

    _print_startup_banner()
    last_sleep_check = time.time()

    # Timer pour détecter le silence continu
    last_voice_time = time.time()
    was_speaking = False

    # Diagnostic counters
    diag_voice_count = 0
    diag_silence_count = 0
    diag_last_report = time.time()
    DIAG_INTERVAL = 10.0

    try:
        while True:
            # Vérifications périodiques (1x par seconde)
            if _should_check_sleep(last_sleep_check):
                check_auto_sleep(ctx)
                check_deep_sleep(ctx)
                last_sleep_check = time.time()

            # =========================================================
            # ÉTAT 1: Système en veille - drain et attendre
            # =========================================================
            if is_sleeping(ctx):
                _drain_audio_queue(ctx)
                # Reset des états
                buffer.clear()
                phrase_detector.reset()
                was_speaking = False
                continue

            # =========================================================
            # ÉTAT 2: Force flush (F8 désactive le micro)
            # =========================================================
            if ctx.force_flush:
                ctx.force_flush = False  # Reset le flag

                if buffer.has_production_audio:
                    print("[ForceFlush] Transcription forcée via F8...")
                    _flush_production(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing)

                was_speaking = False
                continue

            # =========================================================
            # ÉTAT 3: Micro désactivé - drain et attendre
            # =========================================================
            if not ctx.is_recording:
                _drain_audio_queue(ctx)
                # Reset si on vient de désactiver
                if was_speaking:
                    was_speaking = False
                continue

            # =========================================================
            # ÉTAT 4: Système actif + Micro actif - traitement normal
            # =========================================================

            # Get audio block
            audio_block = _get_audio_block(ctx)
            if audio_block is None:
                # Pas d'audio, mais vérifier le silence timeout
                if was_speaking and buffer.has_production_audio:
                    silence_duration = time.time() - last_voice_time
                    if silence_duration >= config.SILENCE_BEFORE_TRANSCRIBE_SECONDS:
                        print(f"[Silence] {silence_duration:.1f}s - Transcription auto")
                        _flush_production(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing)
                        was_speaking = False
                        broadcast_vad(ctx, False)
                continue

            # Detect voice activity
            is_voice = detect_activity(audio_block, ctx.voice_detector)
            phrase_detector.update(audio_block, not is_voice)

            # Broadcast subdivided waveform data (40 Hz for fluid animation)
            _broadcast_waveform_subdivided(ctx, audio_block, is_voice, broadcast_waveform)

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
                      f"Depuis parole: {delta_speech:.1f}s")
                diag_voice_count = 0
                diag_silence_count = 0
                diag_last_report = now

            # =========================================================
            # Traitement de la voix détectée
            # =========================================================
            if is_voice:
                # Voix détectée - accumuler l'audio
                buffer.add_voice_audio(audio_block)
                update_speech_timer(ctx)
                last_voice_time = time.time()

                # Notifier l'UI si on commence à parler
                if not was_speaking:
                    was_speaking = True
                    broadcast_vad(ctx, True)
                    ctx.vad_detecting = True

                # Check for buffer overflow
                if buffer.is_production_overflow:
                    _flush_production_overflow(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing)
                    was_speaking = False
                    broadcast_vad(ctx, False)
                    continue

                # Update preview if enabled
                if config.ENABLE_PREVIEW and preview_manager.should_update():
                    _update_preview(ctx, buffer, preview_manager, broadcast_preview)

            else:
                # Silence détecté
                if was_speaking:
                    # On vient d'arrêter de parler
                    buffer.add_silence()

                    # Vérifier si le silence dépasse le seuil
                    silence_duration = time.time() - last_voice_time
                    if silence_duration >= config.SILENCE_BEFORE_TRANSCRIBE_SECONDS:
                        if buffer.has_production_audio:
                            print(f"[Silence] {silence_duration:.1f}s - Transcription auto")
                            _flush_production(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing)

                        was_speaking = False
                        broadcast_vad(ctx, False)
                        ctx.vad_detecting = False

    except KeyboardInterrupt:
        _handle_shutdown(ctx, buffer, broadcast_preview, broadcast_processing)


# =============================================================================
# Production Flush
# =============================================================================

def _flush_production(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing):
    """Flush production buffer and transcribe."""
    audio = buffer.get_production_audio()
    if audio is None:
        return

    import time as _time
    start_time = _time.time()
    print(f"\n[TRANSCRIPTION] Début - {len(audio)} samples ({len(audio)/config.SAMPLE_RATE:.1f}s audio)")

    try:
        # Notifier l'UI que la transcription commence
        broadcast_processing(ctx, True)
        ctx.is_processing = True
        print("[TRANSCRIPTION] PROCESSING:start envoyé")

        audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)
        print(f"[TRANSCRIPTION] Preprocessing done - {_time.time() - start_time:.2f}s")

        print("\r" + " " * 80 + "\r", end="", flush=True)
        broadcast_preview(ctx, "⏳ Transcription en cours...")

        print("[TRANSCRIPTION] Appel Whisper...")
        whisper_start = _time.time()
        final_text = transcribe_production(ctx, audio)
        whisper_duration = _time.time() - whisper_start
        print(f"[TRANSCRIPTION] Whisper terminé en {whisper_duration:.2f}s")

        if final_text:
            print(f"📋 {final_text}")
            paste_via_clipboard(ctx, final_text)
            broadcast_preview(ctx, f"✅ {final_text}")
        else:
            print("[TRANSCRIPTION] Pas de texte détecté")
            broadcast_preview(ctx, "🎤 En attente de parole...")

    except Exception as exc:
        print(f"[ERROR] Transcription failed: {exc}")
        import traceback
        traceback.print_exc()
        broadcast_preview(ctx, f"❌ Erreur: {str(exc)[:50]}")

    finally:
        # TOUJOURS notifier l'UI que la transcription est terminée
        try:
            broadcast_processing(ctx, False)
            ctx.is_processing = False
            print(f"[TRANSCRIPTION] PROCESSING:done envoyé - Total: {_time.time() - start_time:.2f}s")
        except Exception as e:
            print(f"[ERROR] Failed to send PROCESSING:done: {e}")

        buffer.clear()
        phrase_detector.reset()


def _flush_production_overflow(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing):
    """Handle production buffer overflow."""
    print(f"\n⚠️ Buffer limit ({getattr(config, 'MAX_PRODUCTION_SECONDS', 30)}s) - forcing transcription...")
    _flush_production(ctx, buffer, phrase_detector, broadcast_preview, broadcast_processing)


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
            try:
                broadcast_processing(ctx, True)
                audio = preprocess_audio(audio, sample_rate=config.SAMPLE_RATE, for_production=True)
                final_text = transcribe_production(ctx, audio)
                if final_text:
                    print(f"📋 {final_text}")
                    paste_via_clipboard(ctx, final_text)
            except Exception as exc:
                print(f"[ERROR] Shutdown transcription failed: {exc}")
            finally:
                try:
                    broadcast_processing(ctx, False)
                except Exception:
                    pass

    print("\n👋 Arrêt...")


# =============================================================================
# Banner Messages
# =============================================================================

def _print_startup_banner():
    """Print startup banner."""
    print("\n" + "=" * 60)
    print("🎤 SYSTÈME DE DICTÉE VOCALE")
    print("=" * 60)
    print("   🔊 Système ACTIF par défaut")
    print("   ⌨️  F9 → Activer/Désactiver le système")
    print("   🎤 F8 → Pause/Reprendre micro (force transcription)")
    print(f"   ⏱️  Transcription auto après {config.SILENCE_BEFORE_TRANSCRIBE_SECONDS}s de silence")
    print(f"   💤 Veille auto après {config.AUTO_SLEEP_SECONDS}s d'inactivité")
    print("=" * 60 + "\n")
    print("   Parlez maintenant...")
