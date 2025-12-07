# CLAUDE.md - LLM Knowledge Base

## Project Identity

**Name**: Micro Transcription
**Type**: Real-time speech-to-text system
**Language**: Python 3.12
**Platform**: Linux/Ubuntu (primary), Windows (legacy)
**Core Tech**: faster-whisper, PySide6, Flask SSE, Silero VAD

---

## Architecture Overview

```
main.py                      # Entry point → core.engine.run()
│
├── core/                    # Audio processing & transcription
│   ├── engine.py            # Bootstrap, main loop orchestration
│   ├── processor.py         # Audio pipeline (preview + production)
│   ├── models.py            # Whisper model loading/inference
│   ├── audio_capture.py     # Microphone input, clipboard paste
│   ├── audio_preprocessing.py # Audio filters, normalization
│   ├── voice_detector.py    # Silero VAD + ZCR detection
│   ├── phrase_detector.py   # End-of-phrase detection
│   ├── pipeline.py          # AudioBuffer, PreviewManager, ProductionManager
│   ├── noise_reduction.py   # Spectral noise reduction (optional)
│   └── speaker_detector.py  # Speaker verification (optional)
│
├── api/                     # Inter-process communication
│   ├── server.py            # Flask + SSE broadcasting
│   └── routes/
│       └── transcription.py # /events SSE endpoint
│
├── ui/                      # Qt6 visualizer (subprocess)
│   ├── manager.py           # Subprocess lifecycle
│   └── visualizer_app.py    # PySide6 WebEngine app
│
└── shared/                  # Cross-module utilities
    ├── context.py           # AppContext (global state)
    ├── config.py            # Configuration bridge (exports from settings)
    ├── settings.py          # Pydantic settings (source of truth)
    ├── constants.py         # Shared constants
    ├── interfaces.py        # Protocol definitions + ServiceRegistry
    ├── events.py            # EventBus pub/sub system
    ├── errors.py            # Exception hierarchy + decorators
    ├── sleep.py             # F8/F9 state management
    ├── hotkey.py            # Keyboard hotkey listener
    ├── logger.py            # Logging utilities
    ├── audio_utils.py       # Audio processing utilities
    ├── service_utils.py     # Service accessor helpers
    └── threading_utils.py   # TimeoutLock
```

---

## Core Design Patterns

### 1. AppContext - Centralized State

All mutable state lives in `shared/context.py:AppContext`. Pass `ctx` to every function.

```python
@dataclass
class AppContext:
    # Sub-contexts
    models: ModelContext       # model, model_lock, voice_detector
    sleep: SleepContext        # is_sleeping, is_deep_sleeping, manual_sleep
    audio: AudioContext        # audio_queue, is_recording, production_buffer
    sse: SSEContext            # sse_clients, sse_lock

    # Process management
    visualizer_proc: Optional[subprocess.Popen]
    executor: ThreadPoolExecutor

    # Convenience locks (delegate to sub-contexts)
    @property
    def sleep_lock(self) -> threading.Lock
    @property
    def sse_lock(self) -> threading.Lock
    @property
    def model_lock(self) -> threading.Lock
```

**Pattern**: Never access ctx fields without locks:
```python
with ctx.sleep_lock:
    ctx.is_sleeping = True
```

### 2. ServiceRegistry - Dependency Injection

`shared/interfaces.py:ServiceRegistry` provides runtime service location.

```python
# Registration (in engine.py)
from shared.interfaces import ServiceRegistry, IBroadcaster
ServiceRegistry.register(IBroadcaster, BroadcasterImpl())

# Usage (anywhere)
from shared.service_utils import get_broadcaster
broadcaster = get_broadcaster()
if broadcaster:
    broadcaster.send_preview(ctx, "text")
```

### 3. EventBus - Decoupled Communication

`shared/events.py` implements pub/sub for cross-module events.

```python
from shared.events import EventBus, Events

# Subscribe
def on_transcription(text: str):
    print(f"Got: {text}")
EventBus.subscribe(Events.TRANSCRIPTION_COMPLETE, on_transcription)

# Publish
EventBus.publish(Events.TRANSCRIPTION_COMPLETE, text="Hello")

# Unsubscribe
EventBus.unsubscribe(Events.TRANSCRIPTION_COMPLETE, on_transcription)
```

**Available Events**:
```python
# System state
SYSTEM_ACTIVATED          # F9 ON - system woke up
SYSTEM_DEACTIVATED        # F9 OFF - system went to sleep
DEEP_SLEEP_ENTERED        # Deep sleep mode activated

# Recording
RECORDING_STARTED         # F8 ON - microphone recording
RECORDING_STOPPED         # F8 OFF - microphone paused

# Voice detection
VOICE_DETECTED            # Voice activity detected
SILENCE_DETECTED          # Silence detected
AUDIO_BUFFER_FULL         # Production buffer reached limit

# Model lifecycle
MODEL_LOADING_STARTED     # Whisper model loading started
MODEL_LOADING_COMPLETE    # Whisper model loading finished
MODEL_LOADING_FAILED      # Whisper model loading failed
MODEL_UNLOADED            # Whisper model unloaded (deep sleep)

# Transcription
TRANSCRIPTION_STARTED     # Whisper transcription started
TRANSCRIPTION_COMPLETE    # Transcription finished with result
TRANSCRIPTION_FAILED      # Transcription error
PREVIEW_UPDATED           # Preview text updated

# UI
VISUALIZER_STARTED        # Visualizer window opened
VISUALIZER_CLOSED         # Visualizer window closed

# Calibration
CALIBRATION_STARTED       # VAD calibration started
CALIBRATION_COMPLETE      # VAD calibration finished
```

### 4. Error Handling Decorators

`shared/errors.py` provides centralized error handling.

```python
from shared.errors import handle_errors, ModelLoadError

@handle_errors(log_prefix="[Models]", reraise=True)
def init_models(ctx: AppContext) -> None:
    # Errors logged automatically, re-raised with context
    model = WhisperModel(...)

@handle_errors(log_prefix="[Transcribe]", reraise=False, default_return=None)
def transcribe_audio(audio: np.ndarray) -> Optional[str]:
    # Errors caught, logged, returns None on failure
    return model.transcribe(audio)
```

### 5. Late Imports - Circular Dependency Prevention

Move imports inside functions when circular imports occur:

```python
def activate_system(ctx: AppContext) -> None:
    # Late imports to avoid circular dependencies
    from core.models import init_models
    from ui.manager import start_visualizer

    init_models(ctx)
    start_visualizer(ctx)
```

---

## Data Flow

### Audio Pipeline

```
Microphone (sounddevice)
    │
    ├─► ctx.audio_queue ─► processor.py
    │                          │
    │                     ┌────┴────┐
    │                     │         │
    │               Preview      Production
    │            (every 0.8s)   (on silence)
    │                     │         │
    │               Whisper     Whisper
    │              (fast/approx) (accurate)
    │                     │         │
    │                  SSE ──►    Clipboard
    │                   UI        + Paste
    │                     │         │
    └─────────────────────┴─────────┘
```

### SSE Broadcasting

```python
# api/server.py
def broadcast_preview(ctx: AppContext, text: str) -> None:
    message = f"data: {json.dumps({'preview': text})}\n\n"
    with ctx.sse_lock:
        for client_queue in ctx.sse_clients:
            client_queue.put_nowait(message)

# Usage pattern
from shared.service_utils import get_broadcaster
broadcaster = get_broadcaster()
broadcaster.send_preview(ctx, "transcribed text")
broadcaster.send_state(ctx, "active")  # or "sleep"
broadcaster.send_vad(ctx, True)        # voice detected
broadcaster.send_processing(ctx, True) # whisper running
```

---

## State Management

### F8/F9 Hotkey Logic

```
F9 = System ON/OFF (main toggle)
F8 = Microphone ON/OFF (only when system ON)

States:
- is_sleeping=False, is_recording=True  → Active, recording
- is_sleeping=False, is_recording=False → Active, mic paused (F8)
- is_sleeping=True                      → Sleep mode (F9 OFF)
- is_deep_sleeping=True                 → Deep sleep (models unloaded)
```

**State Transitions** (`shared/sleep.py`):
```python
activate_system(ctx)    # F9 ON: wake up, load models, start visualizer
deactivate_system(ctx)  # F9 OFF: flush audio, close visualizer, sleep
toggle_recording(ctx)   # F8: pause/resume mic (only if system active)
check_auto_sleep(ctx)   # Auto-sleep after 30s inactivity
check_deep_sleep(ctx)   # Deep sleep after 30min (unload models)
```

---

## Module Reference

### core/engine.py
Bootstrap and main loop. Entry point via `run()`.

```python
def run() -> None:
    ctx = create_context()
    start_api_server(ctx)
    start_visualizer(ctx)
    init_models(ctx)
    start_hotkey_listener(ctx)
    run_processor_loop(ctx)  # blocks until shutdown
```

### core/processor.py
Main audio processing loop. Handles preview/production pipelines.

Key functions:
- `run(ctx)` - Main loop
- `_process_audio_block()` - Per-block processing
- `_transcribe_and_paste()` - Production transcription + paste

### core/models.py
Whisper model management.

```python
init_models(ctx)                    # Load Whisper model
unload_models(ctx)                  # Free memory (deep sleep)
transcribe_preview(ctx, audio)      # Fast transcription
transcribe_production(ctx, audio)   # Accurate transcription
```

### core/voice_detector.py
Silero VAD + Zero Crossing Rate for speech detection.

```python
detector = VoiceDetector()
detector.start_calibration()        # Calibrate noise floor
is_speech, prob = detector.is_voice(audio_chunk)
```

### api/server.py
Flask SSE server.

```python
start_server(ctx)                   # Start in background thread
broadcast_preview(ctx, text)        # Send preview to UI
broadcast_state(ctx, "active")      # Send state change
```

### shared/context.py
AppContext dataclass with sub-contexts (ModelContext, SleepContext, AudioContext, SSEContext).

### shared/config.py
Configuration bridge. Exports constants from `settings.py`:
```python
from shared import config
sample_rate = config.SAMPLE_RATE
whisper_model = config.WHISPER_MODEL
```

### shared/settings.py
Pydantic settings - source of truth for all configuration:
```python
from shared.settings import settings
sample_rate = settings.audio.sample_rate
```

---

## Configuration Reference

All configuration is in `shared/config.py` (which delegates to `shared/settings.py`).

### Audio
```python
SAMPLE_RATE = 16000
BLOCK_SECONDS = 0.5
ENERGY_THRESHOLD = 200
SILENCE_BLOCKS_BEFORE_FLUSH = 5
MAX_PRODUCTION_SECONDS = 30
```

### VAD
```python
SILERO_THRESHOLD = 0.1
USE_ZCR_FILTER = True
ZCR_MIN = 0.02
ZCR_MAX = 0.25
```

### Model
```python
WHISPER_MODEL = "large"
DEVICE = "cuda"  # or "cpu"
LANGUAGE = "fr"
BEAM_SIZE = 5
```

### Sleep
```python
AUTO_SLEEP_SECONDS = 30
DEEP_SLEEP_SECONDS = 1800  # 30 minutes
HOTKEY_TOGGLE = "f9"
```

---

## Testing

```bash
# Run all tests
.venv/bin/python -m pytest tests/ -v

# Run specific test file
.venv/bin/python -m pytest tests/test_events.py -v

# Run with coverage
.venv/bin/python -m pytest tests/ --cov=shared --cov=core
```

Test structure mirrors source:
- `tests/test_events.py` → `shared/events.py`
- `tests/test_errors.py` → `shared/errors.py`
- `tests/test_phase4_integration.py` → Integration tests

---

## Common Patterns

### Adding a New Event

1. Add to `shared/events.py:Events`:
```python
class Events(Enum):
    MY_NEW_EVENT = auto()
```

2. Publish where needed:
```python
EventBus.publish(Events.MY_NEW_EVENT, data="value")
```

3. Subscribe in handlers:
```python
EventBus.subscribe(Events.MY_NEW_EVENT, my_handler)
```

### Adding Configuration

1. Add to `shared/settings.py` in appropriate section
2. Export in `shared/config.py`
3. Use via `from shared import config`

### Thread-Safe Operations

```python
from shared.threading_utils import TimeoutLock

lock = TimeoutLock(timeout=5.0, name="my_operation")
with lock:
    # Protected operation
    # Raises TimeoutError if lock not acquired in 5s
```

### Safe Broadcasting

```python
from shared.service_utils import get_broadcaster, broadcast_preview_safe

# Option 1: Check and use
broadcaster = get_broadcaster()
if broadcaster:
    broadcaster.send_preview(ctx, "text")

# Option 2: Safe wrapper (never raises)
broadcast_preview_safe(ctx, "text")  # Returns False if no broadcaster
```

---

## File Naming Conventions

- `config.py` - Module configuration constants
- `settings.py` - Pydantic settings model
- `*_detector.py` - Detection/analysis components
- `*_utils.py` - Utility functions
- `test_*.py` - Test files (mirror source structure)

## Import Conventions

```python
# Standard library
from __future__ import annotations
import threading
from typing import TYPE_CHECKING, Optional

# Third-party
import numpy as np

# Local - always use relative for same package
from .models import transcribe_production
from shared import config
from shared.context import AppContext

# TYPE_CHECKING guard for circular imports
if TYPE_CHECKING:
    from core.voice_detector import VoiceDetector
```
