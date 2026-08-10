# Local voice dictation — micro_transcription

**You speak, the text appears wherever your cursor is.** In any application, without
going through the cloud: speech recognition runs entirely on your machine.

![The visualizer during dictation](docs/images/01-dictee-en-cours.png)

---

## The problem

Dictating text usually means sending your voice to a third party, opening a dedicated
window, then copy-pasting the result. Three points of friction: privacy, context
switching, copy-paste.

This project removes all three. A keyboard shortcut turns on the microphone; as soon
as you pause, the sentence is transcribed and **pasted directly into the active
window** — code editor, browser, chat app. No audio leaves the machine.

The hard part isn't the transcription itself (Whisper handles that), it's **knowing
when you've finished speaking**. Cut too early and you truncate the sentence; cut too
late and the user waits. That's where the logic of this project is concentrated.

---

## How it works

```
Mic ──► Voice detection ──► End-of-phrase detection ──► Whisper ──► Clipboard
        (Silero VAD + ZCR)   (energy + pitch)                        └─► auto-paste
```

**1. Voice activity detection.** Every 0.5 s block runs through Silero VAD (a neural
network, locally), complemented by a zero-crossing-rate filter that rejects music and
non-vocal noise. An adaptive mode learns the ambient noise floor over the first few
seconds and adjusts its thresholds continuously — speech has to stand out by a given
factor above the background.

**2. End-of-phrase detection.** Rather than waiting a fixed delay, the module combines
three cues: silence duration, energy drop, and falling pitch contour (a declarative
sentence ends on a falling intonation). The thresholds are **staged**: the more
acoustic evidence accumulates, the less silence is required.

| Cues available | Silence required |
| --- | --- |
| Silence only | 5 blocks (2.5 s) |
| Silence + energy drop | 3 blocks (1.5 s) |
| Silence + energy + pitch | 2 blocks (1.0 s) |

**3. Transcription.** faster-whisper (CTranslate2) on GPU when available, automatic
fallback to CPU. An anti-hallucination filter discards the artefacts Whisper
characteristically produces on silence ("Subtitled by...", "Thanks for watching").

**4. Pasting.** The text is injected into the active window (xdotool under X11), and
the previous clipboard contents are restored.

---

## Tech stack

| Area | Choice | Why |
| --- | --- | --- |
| Transcription | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) | 4x faster than the reference implementation at equal quality |
| Voice detection | [Silero VAD](https://github.com/snakers4/silero-vad) | 2.2 MB JIT model, loaded locally, no network call |
| Interface | PySide6 / Qt WebEngine | visualizer in an isolated subprocess — the UI cannot freeze the audio loop |
| Communication | Flask + Server-Sent Events | one-way core → UI stream, simpler than a WebSocket here |
| Configuration | pydantic-settings | typed values, validated at the boundaries on startup |
| Audio capture | sounddevice (PortAudio) | real-time callback, low latency |
| Hotkeys | pynput | global capture, works out of focus |

---

## Architecture

```
main.py                    Entry point → core.engine.run()
│
├── core/                  Audio processing and transcription
│   ├── engine.py          Bootstrap, main loop orchestration
│   ├── processor.py       Audio pipeline (preview + production)
│   ├── models.py          Whisper loading, inference, anti-hallucination filter
│   ├── voice_detector.py  Silero VAD + ZCR + adaptive detection
│   ├── phrase_detector.py End-of-phrase detection (energy + pitch)
│   ├── pipeline.py        AudioBuffer, PreviewManager, ProductionManager
│   └── audio_capture.py   Microphone input, clipboard paste
│
├── api/                   Inter-module communication
│   └── server.py          Flask + SSE broadcasting
│
├── ui/                    Qt6 visualizer (subprocess)
│   ├── manager.py         Subprocess lifecycle
│   └── visualizer_app.py  PySide6 WebEngine application
│
└── shared/                Cross-cutting utilities
    ├── context.py         AppContext (global state, lock-guarded sub-contexts)
    ├── settings.py        Pydantic configuration (source of truth)
    └── persistence.py     Persisted settings (parametre.json)
```

Two structural decisions:

- **The visualizer runs in a separate subprocess.** Qt WebEngine is heavy and can
  block; isolating it guarantees the audio capture loop never misses a block.
- **Shared state lives in `AppContext`**, split into sub-contexts (`models`, `sleep`,
  `audio`, `ui`) that each carry their own lock. No mutable field is read or written
  outside its lock.

---

## Installation

Tested on Ubuntu 24.04, Python 3.12.

**1. System dependencies**

```bash
sudo apt install -y xdotool xclip xsel portaudio19-dev \
                    libxcb-xinerama0 libxcb-cursor0 python3-venv
```

`xdotool` handles pasting under X11, `portaudio19-dev` handles microphone capture.

**2. Python environment**

```bash
git clone https://github.com/Skeeder1/micro_transcription.git
cd micro_transcription

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The Whisper model is downloaded on first launch (~460 MB for `small`, ~3 GB for
`large`). Silero VAD (2.2 MB) is fetched once and cached in `.cache/`.

**GPU** — the PyPI `torch` package already bundles CUDA on Linux x86_64. Without an
NVIDIA card the application falls back to CPU on its own (use a `small` or `base`
model in that case).

---

## Configuration

Every setting has a working default: **the `.env` file is optional.**

```bash
cp .env.example .env
```

Naming follows `TRANSCRIBE_<GROUP>__<FIELD>` (double underscore):

```bash
TRANSCRIBE_MODEL__WHISPER_MODEL=small   # tiny|base|small|medium|large
TRANSCRIBE_MODEL__LANGUAGE=fr
TRANSCRIBE_MODEL__DEVICE=cuda           # cuda|cpu|auto
TRANSCRIBE_VAD__SILERO_THRESHOLD=0.1    # lower = more sensitive
TRANSCRIBE_SLEEP__AUTO_SLEEP_SECONDS=30
```

Values are range-validated on startup: an invalid entry fails immediately with an
explicit message, rather than silently degrading behaviour.

```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
audio.sample_rate
  Input should be greater than or equal to 8000 [input_value='999']
```

**No API key is required**: Whisper and Silero run locally.

---

## Running

```bash
source .venv/bin/activate
python main.py
```

Actual startup output:

```
[INFO] 🎤 ADVANCED VOICE DICTATION SYSTEM v2.0
[INFO] 🎯 Initialising advanced voice detector (adaptive mode)...
[INFO] [VAD] Silero VAD loaded (local) (threshold=0.1)
[INFO]    → Automatic ambient noise calibration (first 2 seconds)
[INFO] 🌐 Starting SSE API server...
[INFO] ✅ API server ready!
[INFO] 🚀 Launching graphical interface...
[INFO] [Visualizer] Started (PID: 56698)
[INFO] ⌨️  Hotkeys: F8 = Recording ON/OFF | F9 = Sleep ON/OFF
[INFO] 🎮 Device: CUDA (NVIDIA GPU detected)
[INFO]    Model 'small' loaded successfully
[INFO] 🔊 System ready — speak now!
[INFO] ✅ Audio capture started
```

> Transcribed text is pasted into the **active window**. Put your cursor where you
> want to write before you start speaking.

### Shortcuts

| Key | Effect |
| --- | --- |
| **F9** | System active / asleep (closes the visualizer, releases the mic) |
| **F8** | Mic active / paused (immediately transcribes whatever is buffered) |

Two sleep levels: after 30 s without speech the system goes to sleep; after 30 min it
unloads the models from memory. F9 wakes it back up.

---

## Trying it without a microphone

To verify an installation or measure performance without depending on a mic, a script
pushes an audio file through the real pipeline. With `--generate`, the sentence is
synthesised by ffmpeg — no file needed:

```bash
python scripts/demo_pipeline.py --generate
```

```
======================================================================
TRANSCRIPTION PIPELINE DEMO (no microphone)
======================================================================
File      : demo.wav
Duration  : 4.63 s (74080 samples at 16000 Hz)
Model     : small  |  language: en
Device    : cuda / float16

[1] VOICE ACTIVITY DETECTION  (Silero VAD + zero-crossing rate)
    block  1 @  0.00s : VOICE    silero=0.997  rms=0.1111
    block  2 @  0.50s : VOICE    silero=1.000  rms=0.1683
    block  3 @  1.00s : VOICE    silero=1.000  rms=0.2065
    block  4 @  1.50s : VOICE    silero=1.000  rms=0.2109
    block  5 @  2.00s : VOICE    silero=1.000  rms=0.0987
    block  6 @  2.50s : VOICE    silero=1.000  rms=0.1762
    block  7 @  3.00s : VOICE    silero=1.000  rms=0.1376
    block  8 @  3.50s : VOICE    silero=1.000  rms=0.1739
    block  9 @  4.00s : silence  silero=1.000  rms=0.1312
    -> 8/9 blocks classified as speech

[2] PREPROCESSING  (80 Hz high-pass -> amplification -> normalisation)
    RMS before : 0.1593
    RMS after  : 0.2153
    Duration   : 1.1 ms

[3] WHISPER TRANSCRIPTION
    Model loading : 0.90 s
    Transcription : 0.39 s  (x11.9 real-time factor)

======================================================================
TRANSCRIBED TEXT: 'This project turns your voice into text and pastes it wherever your cursor is.'
======================================================================
```

Measured on an RTX 4060 Laptop, `small` model, float16 precision.

---

## Interface

The visualizer is a compact window, kept on top and designed never to steal focus —
you keep typing while it is open. It gives immediate feedback on what the system
hears and understands.

**Dictation in progress** — the mic is live (blue button), the waveform is coloured by
the VAD decision, and the transcribed text appears beneath the wave.

![Dictation in progress](docs/images/01-dictee-en-cours.png)

**Mic paused (F8)** — the button turns orange. Whatever was still buffered was
transcribed before pausing.

![Mic paused](docs/images/02-micro-en-pause.png)

**Transcription running** — an indicator signals the Whisper pass, so a busy system is
distinguishable from an idle one.

![Transcription running](docs/images/03-transcription-en-cours.png)

**VAD bypass mode** — second button on the bar. Voice detection is short-circuited and
all audio is recorded until the next F8: useful in a noisy environment where the VAD
segments badly. The setting is persisted in `parametre.json`.

![VAD bypass active](docs/images/04-bypass-vad.png)

<sub>Screenshots of the real interface (the project's own HTML/CSS/JS) wired to the
application's SSE server. The waveform is fed from a test audio file rather than a
microphone, to make the captures reproducible.</sub>

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

```
........................................................................ [ 22%]
........................................................................ [ 44%]
........................................................................ [ 67%]
........................................................................ [ 89%]
.................................                                        [100%]
321 passed in 12.93s
```

The suite covers the VAD, end-of-phrase detection, preprocessing, the F8/F9 state
machine, the event bus, error handling and configuration.

`tests/test_end_to_end.py` exercises the full pipeline without a microphone: speech is
synthesised by ffmpeg then pushed through the real components. These tests skip
themselves if ffmpeg is absent. Whisper inference is marked `slow`:

```bash
pytest -m "not slow"    # fast feedback loop
```

---

## Notable technical decisions

**Staged end-of-phrase thresholds.** A single threshold forces a trade-off between
cutting too early and making the user wait. By weighting the required silence against
the available prosodic cues, a clearly finished sentence is transcribed in 1 s while a
hesitation gets 2.5 s. These three thresholds must stay strictly ordered — if they
become equal, the first condition absorbs the others and the prosodic analysis becomes
dead code. A test enforces this.

**Vectorised high-pass filter.** The preprocessing IIR filter is expressible as
`b = [α, -α]`, `a = [1, -α]` and delegated to `scipy.signal.lfilter`, whose loop is in
C: 445 ms → 10 ms on a 30 s buffer, with numerically identical output (max deviation
1.2e-7, i.e. float32 epsilon). A regression test compares the output against the
original Python recurrence.

**Anti-hallucination filter in two families.** Whisper produces characteristic
artefacts on silence. Matching them all as substrings censored legitimate sentences —
"I love music" disappeared because "music" was in the list. Short patterns therefore
only match when they constitute the entire text; only long, unambiguous formulas
("thanks for watching") are searched as substrings.

**Configuration validated at startup.** Failing the launch on an out-of-range value
costs less than diagnosing a VAD that never triggers because of an absurd threshold.

---

## Known limitations

- **X11 only for pasting.** Pasting relies on `xdotool`. Under Wayland, transcription
  works but injection into the active window is unreliable.
- **First launch downloads the model** (~460 MB to ~3 GB): budget for the delay.
- **The `services/` module** (AutoGen integration to reformulate transcribed text) is
  an inactive skeleton.
- **Real-time preview mode** is off by default: it runs a second continuous Whisper
  pass, expensive for limited benefit.

---

## Licence

MIT — see [LICENSE](LICENSE).
