import queue
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
BLOCK_SECONDS = 2.0
ENERGY_THRESHOLD = 0.003
SILENCE_BLOCKS_BEFORE_FLUSH = 2

# 1) Modèle GPU
model = WhisperModel("medium", device="cuda", compute_type="float16")

# 2) Buffer audio
q = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print(status)
    # Convertir en mono 16 kHz float32
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
            if detect_microphone_activity(audio_block):
                buffered_blocks.append(audio_block)
                silence_blocks = 0
                combined = np.concatenate(buffered_blocks, axis=0)
                partial_text = transcribe_array(combined)
                if partial_text and partial_text != current_partial:
                    print(f"\r{partial_text}", end="", flush=True)
                    current_partial = partial_text
                continue

            if buffered_blocks:
                silence_blocks += 1
                if silence_blocks >= SILENCE_BLOCKS_BEFORE_FLUSH:
                    combined = np.concatenate(buffered_blocks, axis=0)
                    clear_partial_line(current_partial)
                    final_text = transcribe_array(combined)
                    if final_text:
                        print(final_text)
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
