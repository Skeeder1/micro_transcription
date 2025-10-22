# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a French voice transcription/dictation system that uses OpenAI's Whisper models for real-time speech-to-text conversion. The system features:

- **Real-time audio visualization** using PySide6 Qt WebEngine with WaveSurfer.js
- **Dual transcription pipeline**: Preview mode (fast, lower quality) and Production mode (high quality)
- **Automatic sleep mode** with intelligent wake-up capabilities
- **Server-Sent Events (SSE)** for real-time communication between components
- **Clipboard integration** for automatic text pasting

## Architecture

### Core Components

The application follows a modular architecture with clear separation of concerns:

- **`transcription_app/app.py`** - Main application orchestrator, initializes all components
- **`transcription_app/main_loop.py`** - Core audio processing loop, manages preview/production pipelines
- **`transcription_app/context.py`** - Shared state container using dataclass with thread-safe locks
- **`transcription_app/audio.py`** - Audio capture, processing, and voice activity detection
- **`transcription_app/models.py`** - Whisper model loading, unloading, and transcription logic
- **`transcription_app/visualizer.py`** - PySide6 Qt interface for real-time audio visualization
- **`transcription_app/sse.py`** - SSE server for real-time communication with visualizer
- **`transcription_app/hotkey.py`** - Global hotkey management (Alt+W, F9 for sleep toggle)
- **`transcription_app/sleep.py`** - Sleep/deep sleep mode management and auto-wake logic

### Data Flow

1. **Audio Capture** → **Voice Detection** → **Queue** → **Main Loop**
2. **Main Loop** → **Preview Pipeline** (fast) → **SSE Broadcast** → **Visualizer**
3. **Main Loop** → **Production Pipeline** (quality) → **Clipboard Paste**
4. **SSE Communication** between backend and Qt WebEngine visualizer
5. **Hotkey/Sleep System** monitors inactivity and manages resource allocation

### Key Design Patterns

- **Thread-safe state management** using locks in AppContext dataclass
- **Producer-consumer pattern** with audio queues for decoupling components
- **Executor pattern** with ThreadPoolExecutor for parallel processing
- **Observer pattern** via SSE for real-time updates
- **Strategy pattern** for different transcription modes (preview vs production)

## Configuration

All configuration is centralized in `transcription_app/config.py` with feature flags:

- **`ENABLE_TRANSCRIPTION`** - Toggle all AI model loading
- **`ENABLE_PREVIEW`** - Enable real-time preview display (currently disabled)
- **`ENABLE_PRODUCTION`** - Enable final high-quality transcription
- **`WHISPER_MODEL`** - Single model used for both modes (currently "large")
- **`DEVICE`** - CUDA for GPU, CPU fallback
- **`SAMPLE_RATE`** - 16kHz for Whisper optimization
- **AUTO_SLEEP_SECONDS** - 10s inactivity before sleep
- **HOTKEY_TOGGLE** - F9 key for manual sleep toggle

## Development Commands

### Running the Application

```bash
# Primary launch method (Windows)
.\run_enhanced.ps1

# Alternative launch methods
python main_enhanced.py
.\start_transcription.bat
```

### Debug Mode

```bash
# Debug mode with enhanced logging
.\start_transcription_debug.bat
```

### Testing Development Changes

```bash
# Install dependencies in virtual environment
.\run_enhanced.ps1  # Auto-checks and installs Flask

# Manual dependency check
.venv\Scripts\python.exe -c "from transcription_app.app import run; print('Import OK')"
```

## Project Structure

```
transcription-audio/
├── main_enhanced.py          # Legacy entry point (delegates to app.py)
├── transcription_app/        # Modular application package
│   ├── __init__.py
│   ├── app.py               # Main orchestrator
│   ├── config.py            # Central configuration
│   ├── context.py           # Shared state
│   ├── main_loop.py         # Core audio processing
│   ├── models.py            # Whisper model management
│   ├── audio.py             # Audio capture and processing
│   ├── visualizer.py        # Qt WebEngine interface
│   ├── sse.py               # SSE server
│   ├── hotkey.py            # Global hotkeys
│   └── sleep.py             # Sleep mode management
├── mic_visualizer_enhanced.py # Legacy visualizer
├── run_enhanced.ps1         # Primary launch script
├── start_transcription.bat  # Windows launcher
├── stop_transcription.bat   # Cleanup script
└── diagnostic_veille.py     # Debug tool for sleep issues
```

## Key Technical Details

### Model Management
- Uses `faster-whisper` for optimized inference
- Single "large" model loaded once, shared between preview and production
- Model unloading in deep sleep mode (600s) to free GPU memory
- Thread-safe model access with locks

### Audio Processing
- 16kHz sampling rate, 500ms blocks
- Voice activity detection using energy threshold
- Silence detection for automatic transcription finalization
- Double buffering approach for preview vs production

### Performance Optimization
- GPU acceleration with CUDA (float16 precision)
- Parallel processing with ThreadPoolExecutor (2 workers)
- Efficient queue-based audio streaming
- SSE for real-time visualizer updates

### Memory Management
- Automatic garbage collection in deep sleep mode
- Resource cleanup on application shutdown
- Clipboard content restoration after pasting

## Environment Setup

Requires Python 3.12.4 with virtual environment in `.venv/`. Key dependencies include:

- `faster-whisper` - Optimized Whisper implementation
- `PySide6` - Qt framework for GUI
- `sounddevice` - Audio capture
- `flask` - SSE server
- `keyboard` - Global hotkeys
- `pyautogui` - Clipboard automation