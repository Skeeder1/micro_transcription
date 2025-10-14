import os
import queue
import subprocess
import sys
import time
import sounddevice as sd
import numpy as np
import keyboard
import pyperclip
from faster_whisper import WhisperModel

_visualizer_proc = None


def start_visualizer():
    """Lance le visualizer en arrière-plan sans fenêtre console visible"""
    global _visualizer_proc
    if _visualizer_proc and _visualizer_proc.poll() is None:
        return
    if _visualizer_proc and _visualizer_proc.poll() is not None:
        _visualizer_proc = None
    
    # Utiliser pythonw.exe au lieu de python.exe pour éviter la console
    exe = os.environ.get("PYTHON_EXE", sys.executable)
    
    # Sur Windows, remplacer python.exe par pythonw.exe
    if exe.endswith('python.exe'):
        pythonw_exe = exe.replace('python.exe', 'pythonw.exe')
        if os.path.exists(pythonw_exe):
            exe = pythonw_exe
    
    # Flags Windows pour processus sans fenêtre
    # CREATE_NO_WINDOW = 0x08000000 (empêche création fenêtre console)
    # DETACHED_PROCESS = 0x00000008 (détache du processus parent)
    startupinfo = None
    creationflags = 0
    
    if sys.platform == 'win32':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        creationflags = 0x08000000 | 0x00000008  # CREATE_NO_WINDOW | DETACHED_PROCESS
    
    _visualizer_proc = subprocess.Popen(
        [exe, "mic_visualizer.py"],
        startupinfo=startupinfo,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def stop_visualizer():
    global _visualizer_proc
    if not _visualizer_proc:
        return
    if _visualizer_proc.poll() is None:
        _visualizer_proc.terminate()
        try:
            _visualizer_proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            pass
    _visualizer_proc = None

SAMPLE_RATE = 16000
BLOCK_SECONDS = 2.0
ENERGY_THRESHOLD = 0.003
SILENCE_BLOCKS_BEFORE_FLUSH = 2

# Comportement collage
RESTORE_CLIPBOARD = True      # restaure l'ancien contenu du presse-papiers
PASTE_DELAY_S = 0.05          # petite latence pour que le presse-papiers soit prêt
APPEND_SPACE = True           # ajoute un espace après chaque insertion
last_pasted = ""              # anti-double collage simple

# 1) Modèle GPU
model = WhisperModel("large", device="cuda", compute_type="float16")

# 2) Buffer audio
q = queue.Queue()

def audio_callback(indata, frames, time_, status):
    if status:
        print(status)
    q.put(indata.copy())

def detect_microphone_activity(audio_block: np.ndarray, threshold: float = ENERGY_THRESHOLD) -> bool:
    """Retourne True si le niveau RMS du bloc dépasse le seuil."""
    rms = float(np.sqrt(np.mean(np.square(audio_block), dtype=np.float64)))
    return rms > threshold

def transcribe_array(audio_array: np.ndarray) -> str:
    """Transcrit un tableau mono et renvoie le texte joint."""
    segments, _ = model.transcribe(audio_array.flatten(),
                                   language="fr", beam_size=1, vad_filter=True)
    return "".join(seg.text for seg in segments).strip()

def clear_partial_line(partial: str) -> None:
    """Efface proprement la ligne partielle affichée."""
    if partial:
        padding = " " * len(partial)
        print(f"\r{padding}\r", end="", flush=True)

def paste_via_clipboard(text: str, restore: bool = RESTORE_CLIPBOARD, append_space: bool = APPEND_SPACE):
    """Copie `text` dans le presse-papiers et déclenche Ctrl+V dans la fenêtre active."""
    if not text:
        return
    payload = text + (" " if append_space and not text.endswith(" ") else "")
    old_clip = None
    if restore:
        try:
            old_clip = pyperclip.paste()
        except pyperclip.PyperclipException:
            old_clip = None
    pyperclip.copy(payload)
    time.sleep(PASTE_DELAY_S)                 # laisse le temps au presse-papiers
    keyboard.press_and_release('ctrl+v')      # colle dans l'app au focus
    if restore and old_clip is not None:
        time.sleep(0.05)
        pyperclip.copy(old_clip)

start_visualizer()
try:
    # 3) Stream micro
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                        blocksize=int(SAMPLE_RATE*BLOCK_SECONDS),
                        callback=audio_callback):
        print("🎙️ Enregistrement... Ctrl+C pour quitter.")
        buffered_blocks = []
        silence_blocks = 0
        current_partial = ""
        try:
            while True:
                # Récupère un bloc audio
                audio_block = q.get()

                # Activité micro : on accumule et on affiche un aperçu incrémental
                if detect_microphone_activity(audio_block):
                    buffered_blocks.append(audio_block)
                    silence_blocks = 0
                    combined = np.concatenate(buffered_blocks, axis=0)
                    partial_text = transcribe_array(combined)
                    if partial_text and partial_text != current_partial:
                        print(f"\r{partial_text}", end="", flush=True)
                        current_partial = partial_text
                    continue

                # Silence : on finalise, on colle via presse-papiers
                if buffered_blocks:
                    silence_blocks += 1
                    if silence_blocks >= SILENCE_BLOCKS_BEFORE_FLUSH:
                        combined = np.concatenate(buffered_blocks, axis=0)
                        clear_partial_line(current_partial)
                        final_text = transcribe_array(combined)
                        if final_text:
                            print(final_text)  # log console (optionnel)
                            if final_text != last_pasted:
                                paste_via_clipboard(final_text)
                                last_pasted = final_text
                        current_partial = ""
                        buffered_blocks.clear()
                        silence_blocks = 0

        except KeyboardInterrupt:
            if buffered_blocks:
                combined = np.concatenate(buffered_blocks, axis=0)
                clear_partial_line(current_partial)
                final_text = transcribe_array(combined)
                if final_text:
                    print(final_text)
                    if final_text != last_pasted:
                        paste_via_clipboard(final_text)
finally:
    stop_visualizer()
