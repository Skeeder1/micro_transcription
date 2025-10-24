# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Advanced speech-to-text transcription system with real-time audio visualization, Whisper-based transcription, and modular architecture prepared for AutoGen integration. The system uses a multi-process architecture with Server-Sent Events (SSE) for inter-module communication.

## Development Commands

### Running the Application

```bash
# Normal launch (background, no console)
python main.py
scripts\start_transcription.bat

# Debug mode (console visible with full logs)
scripts\start_transcription_debug.bat

# Stop all processes
scripts\stop_transcription.bat
```

### Testing and Development

```bash
# Run with virtual environment
.venv\Scripts\python.exe main.py

# Test individual modules
.venv\Scripts\python.exe -m ui.visualizer_app [sse_port]

# Check dependencies
.venv\Scripts\python.exe -c "import flask; import faster_whisper; import PySide6; import sounddevice"
```

### Common Issues

**Windows UTF-8 Encoding**: The application uses emojis and French accented characters. If you see `UnicodeEncodeError`, ensure UTF-8 encoding is configured in the entry point:

```python
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

This is already implemented in `core/engine.py:38-42`.

## Architecture

### Module Structure

The codebase follows a strict modular architecture:

- **core/** - Transcription engine (Whisper models, audio processing)
- **ui/** - Qt6 PySide6 visualizer (subprocess, communicates via SSE)
- **api/** - Flask server for SSE communication between modules
- **shared/** - Shared utilities (config, context, hotkey, sleep)
- **services/** - Future AutoGen integration (stub)

### Critical Architecture Patterns

#### 1. AppContext - Shared State Container

`shared/context.py` defines `AppContext`, a dataclass that holds ALL mutable shared state:

```python
@dataclass
class AppContext:
    visualizer_proc: Optional[subprocess.Popen]  # UI subprocess
    model: Optional[WhisperModel]                # Single Whisper model
    sse_clients: List[queue.Queue]               # SSE client queues
    audio_queue: queue.Queue                     # Audio blocks from sounddevice
    is_sleeping: bool                            # Sleep state
    executor: ThreadPoolExecutor                 # Thread pool
    # ... plus various locks for thread safety
```

**Key insight**: AppContext is passed to ALL major functions and is the single source of truth for application state. When adding features, if you need shared state, add it to AppContext.

#### 2. Configuration System

Configuration is centralized but modular:

- Each module has its own `config.py` (e.g., `core/config.py`, `ui/config.py`)
- `shared/config.py` imports and re-exports ALL configs
- **Always import from shared**: `from shared import config` (never from individual modules)

This prevents circular imports and provides a single namespace for all configuration.

#### 3. Server-Sent Events (SSE) Communication

The UI runs as a **separate subprocess** and communicates via SSE:

```
┌─────────────┐                 ┌─────────────┐
│   Core      │                 │     UI      │
│  (main.py)  │                 │ (subprocess)│
│             │                 │             │
│  ┌────────┐ │   HTTP SSE     │  ┌────────┐ │
│  │ Flask  ├─┼────────────────┼─►│Qt6 App │ │
│  │ Server │ │ /events stream │  │        │ │
│  └────────┘ │                 │  └────────┘ │
└─────────────┘                 └─────────────┘
```

Broadcasting to UI:

```python
from api.server import broadcast_preview, broadcast_state

# Send transcription text
broadcast_preview(ctx, "Transcribed text...")

# Send state changes
broadcast_state(ctx, "sleep")  # or "active"
```

The SSE implementation uses thread-safe queues (`ctx.sse_clients`) to broadcast to all connected clients.

#### 4. Circular Import Prevention

The codebase has strategic late imports to avoid circular dependencies:

```python
# In core/processor.py
def run(ctx: AppContext) -> None:
    # Import here to avoid circular imports
    from shared.sleep import check_auto_sleep
    from api.server import broadcast_preview
    # ... rest of function
```

**When adding imports**: If you encounter circular import errors, move imports inside functions that use them.

#### 5. Audio Pipeline

The audio pipeline has two parallel streams:

```
Audio Input (sounddevice)
    │
    ├─► Preview Buffer  ──► Whisper Small (fast) ──► SSE ──► UI Display
    │
    └─► Production Buffer ──► Whisper Large (accurate) ──► Clipboard ──► Paste
```

- **Preview**: Fast, frequent updates shown in visualizer (may be inaccurate)
- **Production**: Accurate, final transcription pasted to cursor after silence

This is implemented in `core/processor.py:66-150`. The key constants:
- `PREVIEW_UPDATE_INTERVAL`: How often to update preview (default 0.8s)
- `SILENCE_BLOCKS_BEFORE_FLUSH`: How many silent blocks before pasting (default 5)

#### 6. Sleep/Wake State Management

Sleep states are managed in `shared/sleep.py`:

- **Normal sleep** (`is_sleeping=True`): Audio capture paused, models loaded
- **Deep sleep** (`is_deep_sleeping=True`): Models unloaded to save memory (after 10 minutes)

Three ways to enter sleep:
1. Manual toggle via F9 hotkey (`manual_sleep=True`)
2. Auto-sleep after 10s of no speech detected
3. Visualizer closed by user

**Important**: The processor loop checks sleep state frequently and skips audio processing when sleeping. See `core/processor.py:47-52` and `shared/sleep.py`.

#### 7. Thread Safety

Multiple components use threading:

- Audio capture callback (sounddevice thread)
- Main processing loop (main thread)
- Visualizer subprocess (separate process)
- SSE event streams (Flask threads)
- Model loading (background thread)

**All shared state access must be protected**:

```python
with ctx.sleep_lock:
    ctx.is_sleeping = True

with ctx.sse_lock:
    for client in ctx.sse_clients:
        client.put_nowait(message)
```

Never access AppContext fields without appropriate locks.

## Key Files and Their Roles

### Entry Points

- `main.py` - Single entry point, calls `core.engine.run()`
- `core/engine.py` - Bootstraps all modules, starts visualizer, API server, hotkey manager, and main loop

### Core Processing

- `core/processor.py` - Main audio processing loop with preview/production pipelines
- `core/audio_capture.py` - sounddevice callback, VAD detection, clipboard operations
- `core/audio_preprocessing.py` - High-pass filter, normalization, amplification
- `core/models.py` - Whisper model loading and transcription functions

### Communication

- `api/server.py` - Flask server, SSE event streams, `broadcast_preview()`, `broadcast_state()`
- `api/routes/transcription.py` - `/events` endpoint for SSE
- `api/routes/text_processing.py` - Stub endpoints for future AutoGen integration

### UI Management

- `ui/visualizer_app.py` - Qt6 PySide6 app, WebEngine view, SSE client
- `ui/manager.py` - Subprocess management (start/stop visualizer)
- `ui/assets/` - HTML/CSS/JS for waveform visualization and text display

### Shared Utilities

- `shared/context.py` - AppContext dataclass (shared state)
- `shared/config.py` - Centralized configuration
- `shared/hotkey.py` - F9 hotkey listener using pynput
- `shared/sleep.py` - Sleep state transitions and auto-sleep logic

## Configuration Locations

All configuration is in module `config.py` files:

- **Whisper models, audio params, VAD**: `core/config.py`
- **API host, port, CORS**: `api/config.py`
- **Visualizer window, subprocess timeouts**: `ui/config.py`
- **Hotkey, sleep timings**: `shared/config.py`

To change behavior, modify the appropriate config file. Changes are automatically imported via `shared/config.py`.

## Whisper Model Configuration

The system uses **faster-whisper** (optimized Whisper):

- Default model: `large` (2.9GB, best accuracy)
- Device: Auto-detects CUDA GPU, falls back to CPU
- Single model for both preview and production (simplified from v1)

**To change model** in `core/config.py`:

```python
WHISPER_MODEL = "medium"  # or "small", "base", "tiny"
```

Model loading is async (background thread) while UI starts. See `core/engine.py:76-88`.

## Adding Features

### Adding New SSE Message Types

1. Create broadcast function in `api/server.py`
2. Call from core processing loop
3. Handle in `ui/assets/js/visualizer.js` EventSource handler

### Integrating AutoGen

The codebase is prepared for AutoGen integration:

1. Endpoints stubbed in `api/routes/text_processing.py`
2. Configuration example in `services/config.py.example`
3. See `services/README.md` for integration guide

### Adding New Configuration

1. Add to appropriate module's `config.py`
2. Export in `shared/config.py` (add to imports and `__all__`)
3. Use via `from shared import config; config.NEW_PARAM`

## Testing and Debugging

### Debug Mode

Use `scripts\start_transcription_debug.bat` to see:
- All print() statements
- Exception tracebacks
- SSE broadcast messages
- Model loading progress

Console remains open after crash for inspection.

### Checking Process State

```bash
# Check running Python processes
tasklist | findstr python

# Check if visualizer is running
tasklist | findstr python | findstr transcription
```

### Common Debugging Points

- **Audio not capturing**: Check `ENERGY_THRESHOLD` in `core/config.py`
- **Preview not showing**: Check SSE connection in browser console (F12)
- **Paste not working**: Check `RESTORE_CLIPBOARD` and `PASTE_DELAY_SECONDS`
- **High memory usage**: May be in deep sleep, check `is_deep_sleeping` state

## Important Notes

- **Windows-specific**: Uses `pythonw.exe` for background launch, batch scripts for process management
- **GPU support**: Automatically uses CUDA if available, configure in `core/config.py:DEVICE`
- **French language focus**: Default `LANGUAGE = "fr"`, change in `core/config.py` for other languages
- **No pip requirements.txt**: Dependencies are listed in README but not in a requirements file yet

## Future Development: AutoGen Integration

The architecture is prepared for AutoGen text reformulation:

1. Core captures and pastes text (done)
2. UI visualizes transcription (done)
3. API provides SSE transport (done)
4. **TODO**: Add AutoGen agents in `services/` for text reformulation
5. **TODO**: Activate endpoints in `api/routes/text_processing.py`
6. **TODO**: Add UI buttons in visualizer for reformulation triggers

See ARCHITECTURE.md and services/README.md for detailed integration plan.
