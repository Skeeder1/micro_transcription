"""
Système de dictée vocale avancé avec preview temps réel et transcription finale de haute qualité.

Architecture:
- Modèle rapide (base) : Preview <500ms pour retour utilisateur dans le visualizer
- Modèle précis (large) : Transcription finale avec contexte complet pour collage
- Communication SSE : Flask léger pour streamer le texte preview au visualizer
- Double buffering : Buffer court pour preview, buffer complet pour production
"""

import os
import queue
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import keyboard
import numpy as np
import pyperclip
import sounddevice as sd
from faster_whisper import WhisperModel
from flask import Flask, Response

# ============================================================================
# CONFIGURATION
# ============================================================================

# Audio
SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.5  # Blocs plus courts pour meilleure réactivité
ENERGY_THRESHOLD = 0.003
SILENCE_BLOCKS_BEFORE_FLUSH = 3  # ~1.5s de silence

# Preview (retour visuel rapide)
PREVIEW_WINDOW_SECONDS = 3.0  # Fenêtre glissante de 3s pour preview (phrase complète)
PREVIEW_UPDATE_INTERVAL = 1.0  # Update preview toutes les 1s pour stabilité
PREVIEW_TIMEOUT = 8.0  # Timeout preview à 8s (modèle medium plus lent)

# Production (collage final)
RESTORE_CLIPBOARD = True
PASTE_DELAY_S = 0.05
APPEND_SPACE = True

# Serveur SSE
SSE_PORT = 5432
SSE_HOST = '127.0.0.1'

# ============================================================================
# ÉTAT GLOBAL
# ============================================================================

_visualizer_proc: Optional[subprocess.Popen] = None
_preview_model: Optional[WhisperModel] = None
_production_model: Optional[WhisperModel] = None
_sse_clients = []  # Liste des générateurs SSE actifs
_sse_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=2)  # Pour transcriptions parallèles
_last_pasted = ""

audio_queue = queue.Queue()

# ============================================================================
# MODÈLES WHISPER
# ============================================================================

def init_models():
    """Initialise les deux modèles Whisper (rapide et précis)."""
    global _preview_model, _production_model
    
    print("📥 Chargement modèle PREVIEW...")
    # Utiliser 'medium' pour preview avec bonne qualité (compromis qualité/vitesse)
    try:
        print("   Tentative avec modèle 'medium' (meilleur compromis qualité/vitesse)...")
        _preview_model = WhisperModel(
            "medium",
            device="cuda",
            compute_type="float16",
            num_workers=2
        )
        print("   ✅ Modèle 'medium' chargé (preview qualité améliorée)")
    except Exception as e:
        print(f"   ⚠️ Modèle 'medium' non disponible: {e}")
        print("   Utilisation de 'small' à la place...")
        _preview_model = WhisperModel(
            "small",
            device="cuda",
            compute_type="float16",
            num_workers=2
        )
        print("   ✅ Modèle 'small' chargé")
    
    print("📥 Chargement modèle PRODUCTION (large)...")
    _production_model = WhisperModel(
        "large",
        device="cuda",
        compute_type="float16",
        num_workers=2
    )
    
    print("✅ Modèles chargés")


def transcribe_preview(audio_array: np.ndarray) -> str:
    """Transcription rapide pour preview avec modèle medium."""
    if _preview_model is None:
        return ""
    try:
        segments, _ = _preview_model.transcribe(
            audio_array.flatten(),
            language="fr",
            beam_size=3,  # Beam size moyen pour medium (compromis qualité/vitesse)
            vad_filter=True,  # VAD activé pour meilleure qualité
            condition_on_previous_text=False,  # Pas de contexte pour rester rapide
            word_timestamps=False,  # Pas de timestamps
            best_of=2,  # 2 choix pour meilleure qualité
            temperature=0.0  # Déterministe
        )
        return "".join(seg.text for seg in segments).strip()
    except Exception as e:
        print(f"\n⚠️ Preview error: {e}")
        return ""


def transcribe_production(audio_array: np.ndarray) -> str:
    """Transcription finale de haute qualité avec contexte complet."""
    if _production_model is None:
        return ""
    try:
        segments, _ = _production_model.transcribe(
            audio_array.flatten(),
            language="fr",
            beam_size=5,  # Beam search plus large
            vad_filter=True,
            temperature=0.0,  # Déterministe
            condition_on_previous_text=True  # Contexte pour cohérence
        )
        return "".join(seg.text for seg in segments).strip()
    except Exception as e:
        print(f"⚠️ Production error: {e}")
        return ""


# ============================================================================
# SERVEUR SSE (Server-Sent Events)
# ============================================================================

app = Flask(__name__)
app.logger.disabled = True  # Désactive logs Flask


def event_stream():
    """Générateur SSE pour envoyer le texte preview au visualizer."""
    messages = queue.Queue()
    with _sse_lock:
        _sse_clients.append(messages)
        print(f"[SSE] Nouveau client connecté. Total: {len(_sse_clients)}")
    
    try:
        while True:
            msg = messages.get()
            if msg is None:  # Signal d'arrêt
                break
            print(f"[SSE] Envoi message: '{msg[:50]}...'")
            yield f"data: {msg}\n\n"
    finally:
        with _sse_lock:
            _sse_clients.remove(messages)
            print(f"[SSE] Client déconnecté. Restant: {len(_sse_clients)}")


@app.route('/events')
def sse():
    """Endpoint SSE pour streaming de texte."""
    response = Response(event_stream(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response


@app.route('/ping')
def ping():
    """Healthcheck."""
    return 'pong'


def broadcast_preview(text: str):
    """Diffuse le texte preview à tous les clients SSE."""
    with _sse_lock:
        num_clients = len(_sse_clients)
        if num_clients == 0:
            print(f"\n[SSE] Aucun client connecté pour recevoir: '{text[:50]}...'")
        else:
            print(f"\n[SSE] Envoi à {num_clients} client(s): '{text[:50]}...'")
        for client in _sse_clients:
            try:
                client.put_nowait(text)
            except queue.Full:
                pass  # Client trop lent, on skip


def start_sse_server():
    """Démarre le serveur SSE dans un thread séparé."""
    def run():
        from werkzeug.serving import make_server
        server = make_server(SSE_HOST, SSE_PORT, app, threaded=True)
        print(f"🌐 Serveur SSE démarré sur http://{SSE_HOST}:{SSE_PORT}")
        server.serve_forever()
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()


# ============================================================================
# VISUALIZER
# ============================================================================

def start_visualizer():
    """Lance le visualizer avec support SSE."""
    global _visualizer_proc
    if _visualizer_proc and _visualizer_proc.poll() is None:
        return
    if _visualizer_proc and _visualizer_proc.poll() is not None:
        _visualizer_proc = None
    
    exe = os.environ.get("PYTHON_EXE", sys.executable)
    
    # Utiliser pythonw.exe sur Windows
    if exe.endswith('python.exe'):
        pythonw_exe = exe.replace('python.exe', 'pythonw.exe')
        if os.path.exists(pythonw_exe):
            exe = pythonw_exe
    
    startupinfo = None
    creationflags = 0
    
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = 0x08000000 | 0x00000008
    
    # Passer le port SSE en argument
    # Pour debug : ne pas rediriger stderr/stdout
    _visualizer_proc = subprocess.Popen(
        [exe, "mic_visualizer_enhanced.py", str(SSE_PORT)],
        startupinfo=startupinfo,
        creationflags=creationflags
        # stdout et stderr non redirigés pour voir les erreurs
    )


def stop_visualizer():
    """Arrête le visualizer."""
    global _visualizer_proc
    if not _visualizer_proc:
        return
    if _visualizer_proc.poll() is None:
        _visualizer_proc.terminate()
        try:
            _visualizer_proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            _visualizer_proc.kill()
    _visualizer_proc = None


# ============================================================================
# AUDIO & TRANSCRIPTION
# ============================================================================

def audio_callback(indata, frames, time_, status):
    """Callback audio pour sounddevice."""
    if status:
        print(f"⚠️ Audio status: {status}")
    audio_queue.put(indata.copy())


def detect_activity(audio_block: np.ndarray, threshold: float = ENERGY_THRESHOLD) -> bool:
    """Détecte activité vocale via RMS."""
    rms = float(np.sqrt(np.mean(np.square(audio_block), dtype=np.float64)))
    return rms > threshold


def paste_via_clipboard(text: str):
    """Colle le texte via presse-papiers dans l'application active."""
    global _last_pasted
    if not text or text == _last_pasted:
        return
    
    payload = text + (" " if APPEND_SPACE and not text.endswith(" ") else "")
    old_clip = None
    
    if RESTORE_CLIPBOARD:
        try:
            old_clip = pyperclip.paste()
        except pyperclip.PyperclipException:
            pass
    
    pyperclip.copy(payload)
    time.sleep(PASTE_DELAY_S)
    keyboard.press_and_release('ctrl+v')
    
    if RESTORE_CLIPBOARD and old_clip is not None:
        time.sleep(0.05)
        pyperclip.copy(old_clip)
    
    _last_pasted = text


# ============================================================================
# BOUCLE PRINCIPALE
# ============================================================================

def main_loop():
    """Boucle principale avec double buffering et double transcription."""
    
    # Buffers
    preview_buffer = []  # Buffer court pour preview
    production_buffer = []  # Buffer complet pour production
    silence_blocks = 0
    last_preview_update = time.time()
    
    print("🎙️ Écoute active... (Ctrl+C pour quitter)")
    print("   💬 Preview → Visualizer (temps réel)")
    print("   📋 Production → Presse-papiers (haute qualité)")
    
    try:
        while True:
            # Récupérer bloc audio
            audio_block = audio_queue.get()
            
            # Détecter activité
            if detect_activity(audio_block):
                # Activité : accumuler dans les deux buffers
                preview_buffer.append(audio_block)
                production_buffer.append(audio_block)
                silence_blocks = 0
                
                # Limiter taille du buffer preview (fenêtre glissante)
                max_preview_blocks = int(PREVIEW_WINDOW_SECONDS / BLOCK_SECONDS)
                if len(preview_buffer) > max_preview_blocks:
                    preview_buffer.pop(0)
                
                # Update preview périodiquement (pas à chaque bloc)
                now = time.time()
                if now - last_preview_update >= PREVIEW_UPDATE_INTERVAL:
                    if preview_buffer:
                        preview_audio = np.concatenate(preview_buffer, axis=0)
                        # Transcription async pour ne pas bloquer
                        future = _executor.submit(transcribe_preview, preview_audio)
                        try:
                            preview_text = future.result(timeout=PREVIEW_TIMEOUT)
                            if preview_text:
                                broadcast_preview(preview_text)
                                print(f"\r💬 {preview_text}", end="", flush=True)
                        except TimeoutError:
                            # Preview trop lent, on skip ce cycle
                            # (sera mis à jour au prochain intervalle)
                            print(f"\r⏱️ Preview timeout (skip)", end="", flush=True)
                        except Exception as e:
                            # Autre erreur, on continue sans bloquer
                            print(f"\r⚠️ Preview error: {e}", end="", flush=True)
                    last_preview_update = now
                
                continue
            
            # Silence détecté
            if production_buffer:
                silence_blocks += 1
                
                # Flush après suffisamment de silence
                if silence_blocks >= SILENCE_BLOCKS_BEFORE_FLUSH:
                    # Transcription finale haute qualité
                    production_audio = np.concatenate(production_buffer, axis=0)
                    
                    # Effacer preview
                    print("\r" + " " * 80 + "\r", end="", flush=True)
                    broadcast_preview("")  # Clear preview dans visualizer
                    
                    # Transcription production
                    final_text = transcribe_production(production_audio)
                    
                    if final_text:
                        print(f"📋 {final_text}")
                        paste_via_clipboard(final_text)
                    
                    # Reset buffers
                    preview_buffer.clear()
                    production_buffer.clear()
                    silence_blocks = 0
    
    except KeyboardInterrupt:
        # Finaliser buffer restant
        if production_buffer:
            print("\r" + " " * 80 + "\r", end="", flush=True)
            production_audio = np.concatenate(production_buffer, axis=0)
            final_text = transcribe_production(production_audio)
            if final_text:
                print(f"📋 {final_text}")
                paste_via_clipboard(final_text)
        print("\n👋 Arrêt...")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Point d'entrée principal."""
    print("=" * 70)
    print("🎤 SYSTÈME DE DICTÉE VOCALE AVANCÉ")
    print("=" * 70)
    
    # Initialiser modèles
    init_models()
    
    # Démarrer serveur SSE
    start_sse_server()
    time.sleep(1.0)  # Attendre que le serveur démarre
    
    # Vérifier que le serveur SSE répond
    try:
        import urllib.request
        response = urllib.request.urlopen(f'http://{SSE_HOST}:{SSE_PORT}/ping', timeout=2)
        if response.read().decode() == 'pong':
            print("✅ Serveur SSE opérationnel")
        else:
            print("⚠️ Serveur SSE répond mais erreur ping")
    except Exception as e:
        print(f"❌ Serveur SSE ne répond pas: {e}")
        print("⚠️ Le preview ne fonctionnera pas!")
    
    # Démarrer visualizer
    start_visualizer()
    time.sleep(2.0)  # Attendre que le visualizer se connecte
    
    # Envoyer message de test SSE
    print("[TEST] Envoi message de test SSE...")
    broadcast_preview("🔊 Système prêt - Parlez maintenant!")
    time.sleep(1.0)
    
    try:
        # Stream audio
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='float32',
            blocksize=int(SAMPLE_RATE * BLOCK_SECONDS),
            callback=audio_callback
        ):
            main_loop()
    
    finally:
        # Cleanup
        stop_visualizer()
        _executor.shutdown(wait=False)
        print("✅ Nettoyage terminé")


if __name__ == "__main__":
    main()
