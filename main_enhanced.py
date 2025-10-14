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

from pynput import keyboard as pynput_keyboard
import numpy as np
import pyperclip
import sounddevice as sd
from faster_whisper import WhisperModel
from flask import Flask, Response

# ===========================================================================
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

# Veille automatique
AUTO_SLEEP_SECONDS = 10.0  # Veille après 10s sans parole
HOTKEY_TOGGLE = 'alt gr+;'  # Raccourci pour basculer veille/actif (AltGr + point-virgule)
HOTKEY_SEQUENCE_WINDOW = 0.6  # Délai max entre deux pressions de la combinaison (s)

# ============================================================================
# ÉTAT GLOBAL
# ============================================================================

_visualizer_proc: Optional[subprocess.Popen] = None
_visualizer_lock = threading.Lock()  # Protection accès concurrent visualizer
_preview_model: Optional[WhisperModel] = None
_production_model: Optional[WhisperModel] = None
_sse_clients = []  # Liste des générateurs SSE actifs
_sse_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=2)  # Pour transcriptions parallèles
_last_pasted = ""

# États de veille
_is_sleeping = False
_sleep_lock = threading.Lock()
_last_speech_time = time.time()
_last_toggle_time = 0.0  # Protection contre double toggle
_toggle_cooldown = 0.8  # 0.8 secondes entre chaque toggle (réduit pour meilleure réactivité)
_manual_sleep = False  # True si veille manuelle (pas auto)
_is_reactivating = False  # True pendant la réactivation (empêche veille auto)

audio_queue = queue.Queue()

# ============================================================================
# HOTKEY (PYNPUT)
# ============================================================================

_hotkey_listener: Optional[pynput_keyboard.Listener] = None
_hotkey_state_lock = threading.Lock()
_hotkey_state = {
    "alt": False,
    "ctrl": False,
    "altgr": False,
    "semicolon": False,
    "consumed": False,
}
_hotkey_last_press = {
    "alt": 0.0,
    "ctrl": 0.0,
    "altgr": 0.0,
    "semicolon": 0.0,
}

_keyboard_controller = pynput_keyboard.Controller()

_ALT_KEYS = {
    pynput_keyboard.Key.alt,
    pynput_keyboard.Key.alt_l,
    pynput_keyboard.Key.alt_r,
}
_CTRL_KEYS = {
    pynput_keyboard.Key.ctrl,
    pynput_keyboard.Key.ctrl_l,
    pynput_keyboard.Key.ctrl_r,
}


# ============================================================================
# MODÈLES WHISPER
# ============================================================================


def init_models() -> None:
    """Charge les modèles Whisper pour preview et production."""
    global _preview_model, _production_model

    print("📥 Chargement modèle PREVIEW...")
    try:
        _preview_model = WhisperModel(
            "medium",
            device="cuda",
            compute_type="float16",
            num_workers=2,
        )
        print("   ✅ Modèle 'medium' chargé pour le preview")
    except Exception as exc:
        print(f"   ⚠️ Modèle 'medium' indisponible: {exc}")
        print("   ↪️ Utilisation du modèle 'small' en fallback")
        _preview_model = WhisperModel(
            "small",
            device="cuda",
            compute_type="float16",
            num_workers=2,
        )
        print("   ✅ Modèle 'small' chargé")

    print("📥 Chargement modèle PRODUCTION (large)...")
    _production_model = WhisperModel(
        "large",
        device="cuda",
        compute_type="float16",
        num_workers=2,
    )
    print("✅ Modèles chargés")


def transcribe_preview(audio_array: np.ndarray) -> str:
    """Transcription rapide pour preview avec modèle medium/small."""
    if _preview_model is None:
        return ""

    try:
        segments, _ = _preview_model.transcribe(
            audio_array.flatten(),
            language="fr",
            beam_size=3,
            vad_filter=True,
            condition_on_previous_text=False,
            word_timestamps=False,
            best_of=2,
            temperature=0.0,
        )
        return "".join(seg.text for seg in segments).strip()
    except Exception as exc:
        print(f"\n⚠️ Preview error: {exc}")
        return ""


def transcribe_production(audio_array: np.ndarray) -> str:
    """Transcription finale haute qualité avec modèle large."""
    if _production_model is None:
        return ""

    try:
        segments, _ = _production_model.transcribe(
            audio_array.flatten(),
            language="fr",
            beam_size=5,
            vad_filter=True,
            temperature=0.0,
            condition_on_previous_text=True,
        )
        return "".join(seg.text for seg in segments).strip()
    except Exception as exc:
        print(f"⚠️ Production error: {exc}")
        return ""

def _is_semicolon_key(key) -> bool:
    """Retourne True si la touche correspond au point-virgule."""
    if isinstance(key, pynput_keyboard.KeyCode):
        if key.char == ';':
            return True
        vk = getattr(key, "vk", None)
        return vk in (186,)
    return False


def _trigger_toggle_async():
    """Déclenche toggle_sleep_mode dans un thread séparé."""
    threading.Thread(target=toggle_sleep_mode, name="HotkeyToggle", daemon=True).start()


def _handle_hotkey_press(key):
    """Gestion des pressions de touches pour le hotkey AltGr+;."""
    triggered = False
    now = time.monotonic()
    with _hotkey_state_lock:
        try:
            if key == pynput_keyboard.Key.alt_gr:
                _hotkey_state["altgr"] = True
                _hotkey_state["alt"] = True
                _hotkey_state["ctrl"] = True
                _hotkey_last_press["altgr"] = now
                _hotkey_last_press["alt"] = now
                _hotkey_last_press["ctrl"] = now
            elif key in _ALT_KEYS:
                _hotkey_state["alt"] = True
                _hotkey_last_press["alt"] = now
            elif key in _CTRL_KEYS:
                _hotkey_state["ctrl"] = True
                _hotkey_last_press["ctrl"] = now
            elif isinstance(key, pynput_keyboard.KeyCode) and key.char is None:
                pass

            if _is_semicolon_key(key):
                if not _hotkey_state["semicolon"]:
                    _hotkey_state["semicolon"] = True
                _hotkey_last_press["semicolon"] = now

            modifier_active = _hotkey_state["altgr"] or (
                _hotkey_state["alt"] and _hotkey_state["ctrl"]
            )
            modifier_recent = (
                now - _hotkey_last_press["altgr"] <= HOTKEY_SEQUENCE_WINDOW
                or (
                    now - _hotkey_last_press["alt"] <= HOTKEY_SEQUENCE_WINDOW
                    and now - _hotkey_last_press["ctrl"] <= HOTKEY_SEQUENCE_WINDOW
                )
            )
            semicolon_recent = now - _hotkey_last_press["semicolon"] <= HOTKEY_SEQUENCE_WINDOW

            if (
                not _hotkey_state["consumed"]
                and (
                    (
                        _is_semicolon_key(key)
                        and (modifier_active or modifier_recent)
                    )
                    or (
                        key == pynput_keyboard.Key.alt_gr
                        and (_hotkey_state["semicolon"] or semicolon_recent)
                    )
                    or (
                        key in _ALT_KEYS
                        and _hotkey_state["ctrl"]
                        and (_hotkey_state["semicolon"] or semicolon_recent)
                    )
                    or (
                        key in _CTRL_KEYS
                        and _hotkey_state["alt"]
                        and (_hotkey_state["semicolon"] or semicolon_recent)
                    )
                )
            ):
                _hotkey_state["consumed"] = True
                triggered = True

        except AttributeError:
            pass

    if triggered:
        _trigger_toggle_async()


def _handle_hotkey_release(key):
    """Gestion des relâchements de touches pour le hotkey AltGr+;."""
    with _hotkey_state_lock:
        try:
            if key == pynput_keyboard.Key.alt_gr:
                _hotkey_state["altgr"] = False
                _hotkey_state["alt"] = False
                _hotkey_state["ctrl"] = False
            elif key in _ALT_KEYS:
                _hotkey_state["alt"] = False
            elif key in _CTRL_KEYS:
                _hotkey_state["ctrl"] = False

            if _is_semicolon_key(key):
                _hotkey_state["semicolon"] = False
                _hotkey_state["consumed"] = False
            elif not _hotkey_state["semicolon"]:
                if key in _ALT_KEYS or key in _CTRL_KEYS or key == pynput_keyboard.Key.alt_gr:
                    _hotkey_state["consumed"] = False

        except AttributeError:
            pass


def start_hotkey_listener():
    """Démarre le listener pynput pour la combinaison AltGr+;."""
    global _hotkey_listener
    if _hotkey_listener is not None:
        return

    _hotkey_listener = pynput_keyboard.Listener(
        on_press=_handle_hotkey_press,
        on_release=_handle_hotkey_release,
        suppress=False,
    )
    _hotkey_listener.daemon = True
    _hotkey_listener.start()


def stop_hotkey_listener():
    """Arrête le listener pynput si actif."""
    global _hotkey_listener
    if _hotkey_listener is None:
        return

    _hotkey_listener.stop()
    try:
        _hotkey_listener.join(timeout=0.5)
    except RuntimeError:
        pass
    finally:
        _hotkey_listener = None

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
    """Lance le visualizer avec support SSE (thread-safe)."""
    global _visualizer_proc
    
    with _visualizer_lock:
        # Si déjà un process actif, ne rien faire
        if _visualizer_proc and _visualizer_proc.poll() is None:
            print("[Visualizer] Déjà actif, skip")
            return
        
        # Nettoyer ancien process terminé
        if _visualizer_proc:
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
        try:
            _visualizer_proc = subprocess.Popen(
                [exe, "mic_visualizer_enhanced.py", str(SSE_PORT)],
                startupinfo=startupinfo,
                creationflags=creationflags
            )
            print(f"[Visualizer] Lancé (PID: {_visualizer_proc.pid})")
        except Exception as e:
            print(f"[Visualizer] Erreur lancement: {e}")
            _visualizer_proc = None


def stop_visualizer():
    """Arrête le visualizer (thread-safe)."""
    global _visualizer_proc
    
    with _visualizer_lock:
        if not _visualizer_proc:
            return
        
        # Si déjà terminé, juste nettoyer
        if _visualizer_proc.poll() is not None:
            print(f"[Visualizer] Déjà terminé (PID: {_visualizer_proc.pid})")
            _visualizer_proc = None
            return
        
        # Terminer proprement
        print(f"[Visualizer] Arrêt (PID: {_visualizer_proc.pid})...")
        _visualizer_proc.terminate()
        try:
            _visualizer_proc.wait(timeout=2.0)  # Augmenté à 2s pour fiabilité
            print("[Visualizer] Arrêté proprement")
        except subprocess.TimeoutExpired:
            print("[Visualizer] Force kill (timeout)...")
            _visualizer_proc.kill()
            try:
                _visualizer_proc.wait(timeout=1.0)
            except:
                pass  # Si le kill échoue, on abandonne
        except Exception as e:
            print(f"[Visualizer] Erreur arrêt: {e}")
        finally:
            _visualizer_proc = None  # TOUJOURS nettoyer la référence


# ============================================================================
# GESTION DE LA VEILLE
# ============================================================================

def enter_sleep_mode(manual=False):
    """Met le système en veille."""
    global _is_sleeping, _manual_sleep
    
    # Vérifier si déjà en veille
    with _sleep_lock:
        if _is_sleeping:
            print("[Veille] Déjà en veille, skip")
            return
        _is_sleeping = True
        _manual_sleep = manual  # Mémoriser si veille manuelle
    
    print("\n💤 Mode VEILLE activé" + (" (manuel)" if manual else " (auto)"))
    print(f"   Appuyez sur {HOTKEY_TOGGLE.upper()} pour réactiver")
    
    # Arrêter visualizer proprement
    stop_visualizer()
    broadcast_preview("")  # Clear preview


def exit_sleep_mode():
    """Sort du mode veille."""
    global _is_sleeping, _last_speech_time, _manual_sleep, _is_reactivating
    
    # Reset timer IMMÉDIATEMENT pour éviter veille auto pendant réactivation
    _last_speech_time = time.time()
    
    # Bloquer veille auto pendant réactivation
    _is_reactivating = True
    
    try:
        # Vérifier si déjà actif
        with _sleep_lock:
            if not _is_sleeping:
                print("[Veille] Déjà actif, skip")
                _is_reactivating = False  # IMPORTANT: Reset flag même en cas de skip
                return
            _is_sleeping = False
            _manual_sleep = False  # Reset flag manuel
        
        print("\n🔊 Mode ACTIF - Système réactivé")
        
        # S'assurer que l'ancien visualizer est bien arrêté
        print("[Veille] Nettoyage préalable...")
        stop_visualizer()
        time.sleep(0.3)  # Petit délai pour que le port se libère
        
        # Lancer visualizer (avec protection contre duplication)
        start_visualizer()
        
        # Attendre que le visualizer soit prêt
        print("[Veille] Attente connexion visualizer...")
        time.sleep(2.5)  # Augmenté pour stabilité
        
        # Envoyer message de réactivation
        broadcast_preview("🔊 Système réactivé - Parlez maintenant!")
        print("[Veille] Réactivation complète")
    
    except Exception as e:
        print(f"⚠️ Erreur pendant réactivation: {e}")
        # En cas d'erreur, forcer l'état pour permettre un nouveau toggle
        with _sleep_lock:
            _is_sleeping = False
        _is_reactivating = False
        raise
    
    finally:
        # Débloquer veille auto (TOUJOURS)
        _is_reactivating = False


def toggle_sleep_mode():
    """Bascule entre veille et actif avec protection anti-rebond."""
    global _last_toggle_time
    
    # Protection anti-rebond (debounce)
    current_time = time.time()
    time_since_last_toggle = current_time - _last_toggle_time
    
    if time_since_last_toggle < _toggle_cooldown:
        print(f"[Toggle] Cooldown actif ({time_since_last_toggle:.2f}s < {_toggle_cooldown}s) - Ignoré")
        return
    
    _last_toggle_time = current_time
    
    # Déterminer l'état actuel
    with _sleep_lock:
        sleeping = _is_sleeping
        reactivating = _is_reactivating
    
    # Ne pas permettre toggle pendant réactivation en cours
    if reactivating:
        print("[Toggle] Réactivation en cours, veuillez patienter...")
        return
    
    print(f"[Toggle] État actuel: {'VEILLE' if sleeping else 'ACTIF'} → {'ACTIF' if sleeping else 'VEILLE'}")
    
    try:
        if sleeping:
            exit_sleep_mode()
        else:
            enter_sleep_mode(manual=True)  # Veille manuelle via hotkey
    except Exception as e:
        print(f"❌ Erreur toggle: {e}")
        # Reset des flags de sécurité en cas d'erreur
        _last_toggle_time = 0.0  # Permettre retry immédiat


def check_auto_sleep():
    """Vérifie si veille automatique doit s'activer."""
    global _last_speech_time
    
    # Ne pas vérifier pendant réactivation
    if _is_reactivating:
        return
    
    with _sleep_lock:
        if _is_sleeping:
            return
    
    time_since_speech = time.time() - _last_speech_time
    if time_since_speech > AUTO_SLEEP_SECONDS:
        print(f"\n⏰ Inactivité détectée ({AUTO_SLEEP_SECONDS}s)")
        enter_sleep_mode()


def update_speech_timer():
    """Met à jour le timer de dernière parole détectée."""
    global _last_speech_time
    _last_speech_time = time.time()


def is_sleeping() -> bool:
    """Retourne True si en mode veille."""
    with _sleep_lock:
        return _is_sleeping


def check_visualizer_closed():
    """Vérifie si le visualizer s'est fermé et entre en veille (thread-safe)."""
    
    # Si déjà en veille, rien à faire
    if is_sleeping():
        return
    
    # Vérifier si veille manuelle en cours
    with _sleep_lock:
        if _manual_sleep:
            # Veille manuelle, ne pas réagir à la fermeture
            return
    
    # Vérifier le process avec le lock
    with _visualizer_lock:
        if not _visualizer_proc:
            return
        
        # Si process terminé, marquer pour veille
        should_sleep = _visualizer_proc.poll() is not None
    
    # Appel hors du lock pour éviter deadlock
    if should_sleep:
        print("\n🪟 Visualizer fermé (détection auto)")
        enter_sleep_mode(manual=False)  # Veille auto via fermeture


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

    try:
        _keyboard_controller.press(pynput_keyboard.Key.ctrl)
        _keyboard_controller.press('v')
        _keyboard_controller.release('v')
        _keyboard_controller.release(pynput_keyboard.Key.ctrl)
    except Exception as exc:
        print(f"⚠️ Erreur envoi Ctrl+V: {exc}")
    
    if RESTORE_CLIPBOARD and old_clip is not None:
        time.sleep(0.05)
        pyperclip.copy(old_clip)
    
    _last_pasted = text


# ============================================================================
# BOUCLE PRINCIPALE
# ============================================================================

def main_loop():
    """Boucle principale avec double buffering, double transcription et gestion veille."""
    
    # Buffers
    preview_buffer = []  # Buffer court pour preview
    production_buffer = []  # Buffer complet pour production
    silence_blocks = 0
    last_preview_update = time.time()
    last_sleep_check = time.time()
    
    print("🎙️ Écoute active... (Ctrl+C pour quitter)")
    print(f"   💬 Preview → Visualizer (temps réel)")
    print(f"   📋 Production → Presse-papiers (haute qualité)")
    print(f"   💤 {HOTKEY_TOGGLE.upper()} → Basculer veille/actif")
    print(f"   ⏰ Veille auto après {AUTO_SLEEP_SECONDS}s d'inactivité")
    
    try:
        while True:
            # Vérifier veille auto périodiquement
            now = time.time()
            if now - last_sleep_check >= 1.0:
                check_auto_sleep()
                check_visualizer_closed()  # Veille si visualizer fermé
                last_sleep_check = now
            
            # Si en veille, vider la queue audio sans traiter
            if is_sleeping():
                try:
                    audio_queue.get(timeout=0.1)
                except queue.Empty:
                    pass
                continue
            
            # Récupérer bloc audio
            try:
                audio_block = audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            
            # Détecter activité
            if detect_activity(audio_block):
                # Activité : accumuler dans les deux buffers
                preview_buffer.append(audio_block)
                production_buffer.append(audio_block)
                silence_blocks = 0
                
                # Mettre à jour timer de parole (évite veille auto)
                update_speech_timer()
                
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
    
    # Enregistrer hotkey pour veille/réveil via pynput
    print(f"⌨️  Initialisation hotkey {HOTKEY_TOGGLE.upper()} (pynput)...")
    start_hotkey_listener()
    print(f"✅ Hotkey {HOTKEY_TOGGLE.upper()} prêt (bascule veille/actif)")
    
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
        stop_hotkey_listener()
        stop_visualizer()
        _executor.shutdown(wait=False)
        print("✅ Nettoyage terminé")


if __name__ == "__main__":
    main()
