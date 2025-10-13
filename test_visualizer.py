"""Test rapide du visualiseur sans Whisper"""
import os
import subprocess
import sys
import time

_visualizer_proc = None

def start_visualizer():
    global _visualizer_proc
    if _visualizer_proc and _visualizer_proc.poll() is None:
        print("Visualizer déjà en cours")
        return
    if _visualizer_proc and _visualizer_proc.poll() is not None:
        _visualizer_proc = None
    exe = os.environ.get("PYTHON_EXE", sys.executable)
    print(f"Démarrage visualizer avec {exe}")
    _visualizer_proc = subprocess.Popen([exe, "mic_visualizer.py"], creationflags=0x00000008)
    print(f"Visualizer PID: {_visualizer_proc.pid}")

def stop_visualizer():
    global _visualizer_proc
    if not _visualizer_proc:
        print("Aucun visualizer à arrêter")
        return
    if _visualizer_proc.poll() is None:
        print("Arrêt du visualizer...")
        _visualizer_proc.terminate()
        try:
            _visualizer_proc.wait(timeout=1.0)
            print("Visualizer arrêté")
        except subprocess.TimeoutExpired:
            print("Timeout, forçage...")
            _visualizer_proc.kill()
    _visualizer_proc = None

if __name__ == "__main__":
    print("=== Test Visualizer ===")
    print("Démarrage dans 2 secondes...")
    time.sleep(2)
    
    start_visualizer()
    
    print("\nVisualizer lancé. Appuyez sur Entrée pour arrêter...")
    input()
    
    stop_visualizer()
    print("Test terminé.")
