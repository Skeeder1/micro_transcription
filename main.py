import queue
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
BLOCK_SECONDS = 2.0
ENERGY_THRESHOLD = 0.01
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

# 3) Stream micro
with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                    blocksize=int(SAMPLE_RATE*BLOCK_SECONDS),
                    callback=audio_callback):
    print("🎙️ Enregistrement... Ctrl+C pour quitter.")
    buffered_blocks = []
    silence_blocks = 0
    try:
        while True:
            # Récupère un bloc audio
            audio_block = q.get()
            if detect_microphone_activity(audio_block):
                buffered_blocks.append(audio_block)
                silence_blocks = 0
                continue

            if buffered_blocks:
                silence_blocks += 1
                if silence_blocks >= SILENCE_BLOCKS_BEFORE_FLUSH:
                    combined = np.concatenate(buffered_blocks, axis=0)
                    segments, info = model.transcribe(combined.flatten(),
                                                      language="fr", beam_size=1, vad_filter=True)
                    text = "".join([seg.text for seg in segments]).strip()
                    if text:
                        print(text)
                    buffered_blocks.clear()
                    silence_blocks = 0
    except KeyboardInterrupt:
        if buffered_blocks:
            combined = np.concatenate(buffered_blocks, axis=0)
            segments, info = model.transcribe(combined.flatten(),
                                              language="fr", beam_size=1, vad_filter=True)
            text = "".join([seg.text for seg in segments]).strip()
            if text:
                print(text)
