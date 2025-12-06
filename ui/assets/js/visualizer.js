/* Micro Transcription - Visualizer JavaScript */
/* Custom Canvas Waveform with Web Audio API - bypasses WaveSurfer issues in QtWebEngine */

(function() {
'use strict';

console.log('[Visualizer] Starting...');

// ===========================================
// DOM Elements
// ===========================================

const panel = document.querySelector('.panel');
const recBtn = document.querySelector('#rec-btn');
const recIcon = document.querySelector('.rec-icon');
const statusLabel = document.querySelector('#status');
const statusSpinner = document.querySelector('#status-spinner');
const previewText = document.querySelector('#preview-text');
const previewContainer = document.querySelector('#preview-container');
const sseStatus = document.querySelector('#sse-status');
const errorDiv = document.querySelector('#error');
const waveformCanvas = document.querySelector('#waveform-canvas');

console.log('[Visualizer] DOM elements selected');
console.log('[Visualizer] Canvas element:', waveformCanvas ? 'found' : 'NOT FOUND');

// ===========================================
// Audio State
// ===========================================

let microphoneStream = null;
let audioContext = null;
let audioAnalyzer = null;
let animationId = null;
let isCapturing = false;

// Waveform history for scrolling effect
const HISTORY_LENGTH = 150;
let waveformHistory = new Array(HISTORY_LENGTH).fill(0);

// ===========================================
// SSE State
// ===========================================

let eventSource = null;
let sseReconnectTimer = null;

// ===========================================
// Status Management
// ===========================================

const showError = (msg) => {
  if (errorDiv) {
    errorDiv.textContent = msg;
    console.error('[Error]', msg);
  }
  setStatus(msg, 'error');
};

const setStatus = (msg, type = 'normal') => {
  if (statusLabel) {
    statusLabel.textContent = msg;
    statusLabel.className = type;
  }
};

// ===========================================
// Preview Text
// ===========================================

const updatePreview = (text) => {
  if (!previewText || !previewContainer) return;

  if (!text || text.trim() === '') {
    previewText.textContent = 'En attente de parole...';
    previewText.classList.add('empty');
    previewContainer.classList.remove('has-text');
  } else {
    previewText.textContent = text;
    previewText.classList.remove('empty');
    previewContainer.classList.add('has-text');
    previewContainer.scrollTop = previewContainer.scrollHeight;
  }
};

// ===========================================
// State Handlers
// ===========================================

const handleStateChange = (state) => {
  if (state === 'sleep') {
    console.log('[State] Entering sleep mode');
    panel.classList.add('sleeping');
    updatePreview('Mode veille - Appuyez sur F9');
    setStatus('Mode veille', 'warning');
    if (window.qtBridge) {
      window.qtBridge.handleStateChange('sleep');
    }
  } else if (state === 'active') {
    console.log('[State] Exiting sleep mode');
    panel.classList.remove('sleeping');
    updatePreview('Systeme actif - Parlez maintenant!');
    setStatus('Actif', 'active');
    if (window.qtBridge) {
      window.qtBridge.handleStateChange('active');
    }
  }
};

const handleRecordingChange = (state) => {
  if (state === 'recording') {
    console.log('[Recording] Microphone active');
    if (recBtn) {
      recBtn.classList.remove('rec-paused');
      recBtn.classList.add('rec-active');
      // Reset VAD state to inactive when starting (will be updated by VAD events)
      recBtn.classList.add('vad-inactive');
    }
    if (recIcon) recIcon.textContent = '🎤';
    if (recBtn) recBtn.title = 'Micro actif (F8 pour pause)';
    setStatus('Micro actif', 'active');
  } else if (state === 'paused') {
    console.log('[Recording] Microphone paused');
    if (recBtn) {
      recBtn.classList.remove('rec-active');
      recBtn.classList.remove('vad-active');
      recBtn.classList.remove('vad-inactive');
      recBtn.classList.add('rec-paused');
    }
    if (recIcon) recIcon.textContent = '⏸️';
    if (recBtn) recBtn.title = 'Micro en pause (F8 pour reprendre)';
    setStatus('Micro en pause', 'warning');
  }
};

const handleVADChange = (state) => {
  // Update mic button VAD state (blue vif = VAD active, gris-bleu = VAD inactive)
  if (recBtn) {
    if (state === 'active') {
      recBtn.classList.remove('vad-inactive');
      recBtn.classList.add('vad-active');
    } else {
      recBtn.classList.remove('vad-active');
      recBtn.classList.add('vad-inactive');
    }
  }
};

let processingTimeout = null;

const handleProcessingChange = (state) => {
  if (processingTimeout) {
    clearTimeout(processingTimeout);
    processingTimeout = null;
  }

  if (state === 'start') {
    console.log('[Processing] Transcription started');
    // Show spinner next to status
    if (statusSpinner) statusSpinner.classList.remove('hidden');
    setStatus('Transcription...', 'active');
    processingTimeout = setTimeout(() => {
      console.warn('[Processing] Timeout - forcing reset');
      if (statusSpinner) statusSpinner.classList.add('hidden');
      setStatus('Actif', 'active');
    }, 30000);
  } else if (state === 'done') {
    console.log('[Processing] Transcription complete');
    // Hide spinner
    if (statusSpinner) statusSpinner.classList.add('hidden');
    setStatus('Actif', 'active');
  }
};

// ===========================================
// SSE Connection
// ===========================================

const closeSSE = () => {
  if (sseReconnectTimer) {
    clearTimeout(sseReconnectTimer);
    sseReconnectTimer = null;
  }
  if (eventSource) {
    eventSource.onopen = null;
    eventSource.onmessage = null;
    eventSource.onerror = null;
    eventSource.close();
    eventSource = null;
  }
};

const connectSSE = () => {
  closeSSE();

  const ssePort = window.SSE_PORT || 5433;
  console.log('[SSE] Connecting to http://127.0.0.1:' + ssePort + '/events');

  eventSource = new EventSource('http://127.0.0.1:' + ssePort + '/events');

  eventSource.onopen = () => {
    console.log('[SSE] Connected');
    if (sseStatus) sseStatus.classList.add('connected');
    setStatus('Connecte', 'active');
  };

  eventSource.onmessage = (event) => {
    if (event.data.startsWith('STATE:')) {
      console.log('[SSE] Received:', event.data);
      handleStateChange(event.data.substring(6));
    } else if (event.data.startsWith('RECORDING:')) {
      console.log('[SSE] Received:', event.data);
      handleRecordingChange(event.data.substring(10));
    } else if (event.data.startsWith('VAD:')) {
      handleVADChange(event.data.substring(4));
    } else if (event.data.startsWith('PROCESSING:')) {
      console.log('[SSE] Received:', event.data);
      handleProcessingChange(event.data.substring(11));
    } else {
      console.log('[SSE] Received:', event.data);
      updatePreview(event.data);
    }
  };

  eventSource.onerror = (error) => {
    console.error('[SSE] Error:', error);
    if (sseStatus) sseStatus.classList.remove('connected');
    setStatus('Reconnexion...', 'warning');

    if (!sseReconnectTimer) {
      sseReconnectTimer = setTimeout(() => {
        sseReconnectTimer = null;
        console.log('[SSE] Reconnecting...');
        connectSSE();
      }, 3000);
    }
  };
};

// ===========================================
// Initial State Sync
// ===========================================

const syncInitialState = async () => {
  const ssePort = window.SSE_PORT || 5433;
  try {
    const resp = await fetch('http://127.0.0.1:' + ssePort + '/status');
    if (resp.ok) {
      const data = await resp.json();
      console.log('[Init] Syncing state:', data);
      handleRecordingChange(data.is_recording ? 'recording' : 'paused');
      handleStateChange(data.is_sleeping ? 'sleep' : 'active');
    }
  } catch (e) {
    console.warn('[Init] Could not sync initial state:', e);
  }
};

// ===========================================
// Canvas Waveform Setup
// ===========================================

const setupCanvas = () => {
  if (!waveformCanvas) {
    console.error('[Canvas] Canvas element not found!');
    return false;
  }

  // Set actual canvas dimensions (not just CSS)
  const rect = waveformCanvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  waveformCanvas.width = rect.width * dpr;
  waveformCanvas.height = rect.height * dpr;

  console.log('[Canvas] Initialized:', waveformCanvas.width, 'x', waveformCanvas.height, '(DPR:', dpr + ')');
  return true;
};

const drawWaveform = () => {
  if (!waveformCanvas) {
    animationId = requestAnimationFrame(drawWaveform);
    return;
  }

  const ctx = waveformCanvas.getContext('2d');
  const width = waveformCanvas.width;
  const height = waveformCanvas.height;
  const dpr = window.devicePixelRatio || 1;

  // Get frequency data if analyzer exists
  if (audioAnalyzer) {
    const bufferLength = audioAnalyzer.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    audioAnalyzer.getByteFrequencyData(dataArray);

    // Calculate average level for current frame
    let sum = 0;
    for (let i = 0; i < bufferLength; i++) {
      sum += dataArray[i];
    }
    const average = sum / bufferLength;

    // Add to history (shift left, add new value at end)
    waveformHistory.shift();
    waveformHistory.push(average);
  }

  // Clear canvas
  ctx.fillStyle = '#1a1a1a';
  ctx.fillRect(0, 0, width, height);

  // Draw waveform bars
  const barWidth = width / HISTORY_LENGTH;
  const barGap = 1 * dpr;
  const actualBarWidth = Math.max(barWidth - barGap, 2);

  for (let i = 0; i < HISTORY_LENGTH; i++) {
    const value = waveformHistory[i];

    // Normalize and amplify (0-255 -> 0-1, then scale)
    const normalized = value / 255;
    const amplified = Math.pow(normalized, 0.6) * 1.8;  // Amplify quieter sounds

    // Calculate bar height (minimum 2px for visibility)
    const barHeight = Math.max(amplified * height * 0.85, 2 * dpr);

    // Position bar centered vertically
    const x = i * barWidth;
    const y = (height - barHeight) / 2;

    // Color gradient based on intensity
    const intensity = Math.min(normalized * 2.5, 1);
    const r = Math.floor(100 + intensity * 155);  // 100 -> 255
    const g = Math.floor(200 - intensity * 50);   // 200 -> 150
    const b = Math.floor(255 - intensity * 100);  // 255 -> 155

    ctx.fillStyle = 'rgb(' + r + ', ' + g + ', ' + b + ')';

    // Draw rounded bar
    ctx.beginPath();
    const radius = Math.min(actualBarWidth / 2, 3 * dpr);
    ctx.roundRect(x, y, actualBarWidth, barHeight, radius);
    ctx.fill();
  }

  // Continue animation
  animationId = requestAnimationFrame(drawWaveform);
};

// ===========================================
// Audio Capture
// ===========================================

const startAudioCapture = async () => {
  if (isCapturing) {
    console.log('[Audio] Already capturing');
    return true;
  }

  try {
    console.log('[Audio] Requesting microphone access...');

    // Close existing stream if any
    if (microphoneStream) {
      microphoneStream.getTracks().forEach(track => track.stop());
      microphoneStream = null;
    }

    // Close existing audio context
    if (audioContext) {
      try {
        await audioContext.close();
      } catch (e) {
        console.warn('[Audio] Error closing old context:', e);
      }
    }

    // Request microphone access
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        sampleRate: 48000,
      }
    });

    const tracks = microphoneStream.getAudioTracks();
    console.log('[Audio] Got stream with', tracks.length, 'audio tracks');

    if (tracks.length > 0) {
      const track = tracks[0];
      console.log('[Audio] Track:', track.label);
      console.log('[Audio] Track enabled:', track.enabled, 'muted:', track.muted);
    }

    // Create audio context and analyzer
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(microphoneStream);

    audioAnalyzer = audioContext.createAnalyser();
    audioAnalyzer.fftSize = 256;
    audioAnalyzer.smoothingTimeConstant = 0.4;

    source.connect(audioAnalyzer);

    console.log('[Audio] Analyzer created, FFT size:', audioAnalyzer.fftSize);
    console.log('[Audio] Frequency bins:', audioAnalyzer.frequencyBinCount);

    // Diagnostic: verify audio levels periodically
    let diagCount = 0;
    const diagInterval = setInterval(() => {
      if (!audioAnalyzer || diagCount >= 5) {
        clearInterval(diagInterval);
        return;
      }
      diagCount++;

      const dataArray = new Uint8Array(audioAnalyzer.frequencyBinCount);
      audioAnalyzer.getByteFrequencyData(dataArray);
      const avg = dataArray.reduce((a, b) => a + b) / dataArray.length;
      const max = Math.max.apply(null, dataArray);

      console.log('[Audio] Level check #' + diagCount + ': avg=' + avg.toFixed(1) + ', max=' + max);

      if (avg < 1 && diagCount >= 3) {
        console.warn('[Audio] WARNING: Very low audio levels - check microphone');
      }
    }, 1000);

    isCapturing = true;
    console.log('[Audio] Capture started successfully');
    return true;

  } catch (err) {
    console.error('[Audio] Error getting microphone:', err);
    showError('Erreur micro: ' + err.message);
    return false;
  }
};

const stopAudioCapture = () => {
  isCapturing = false;

  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }

  if (audioContext) {
    try {
      audioContext.close();
    } catch (e) {
      console.warn('[Audio] Error closing context:', e);
    }
    audioContext = null;
    audioAnalyzer = null;
  }

  if (microphoneStream) {
    microphoneStream.getTracks().forEach(track => {
      track.stop();
      console.log('[Audio] Stopped track:', track.label);
    });
    microphoneStream = null;
  }

  // Clear waveform history
  waveformHistory = new Array(HISTORY_LENGTH).fill(0);

  // Clear canvas
  if (waveformCanvas) {
    const ctx = waveformCanvas.getContext('2d');
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, waveformCanvas.width, waveformCanvas.height);
  }

  console.log('[Audio] Capture stopped');
};

// ===========================================
// Initialization
// ===========================================

const initialize = async () => {
  try {
    console.log('[Init] Initializing visualizer...');

    // Qt WebChannel
    if (typeof QWebChannel !== 'undefined' && window.qt && window.qt.webChannelTransport) {
      new QWebChannel(window.qt.webChannelTransport, function(channel) {
        window.qtBridge = channel.objects.qtBridge;
        console.log('[Init] Qt WebChannel initialized');
      });
    } else {
      console.warn('[Init] Qt WebChannel not available');
    }

    // Setup canvas
    if (!setupCanvas()) {
      showError('Canvas non trouve');
      return;
    }

    // Start audio capture
    console.log('[Init] Starting audio capture...');
    const success = await startAudioCapture();

    if (!success) {
      showError('Impossible d\'acceder au microphone');
      return;
    }

    // Start waveform animation
    console.log('[Init] Starting waveform animation...');
    drawWaveform();

    // Connect SSE
    connectSSE();

    // Sync initial state from backend
    await syncInitialState();

    console.log('[Init] Initialization complete - waveform should be visible!');

  } catch (err) {
    showError('Init error: ' + err.message);
    console.error('[Init] Error:', err);
  }
};

// ===========================================
// Bridge for External Control
// ===========================================

window.visualizerBridge = {
  start: async () => {
    if (isCapturing) {
      console.log('[Bridge] Already capturing');
      return;
    }
    const success = await startAudioCapture();
    if (success && !animationId) {
      drawWaveform();
    }
  },
  stop: stopAudioCapture,
  updatePreview: updatePreview,
  toggle: () => {
    if (isCapturing) {
      stopAudioCapture();
    } else {
      window.visualizerBridge.start();
    }
  }
};

// ===========================================
// Start
// ===========================================

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initialize, 100);
  });
} else {
  setTimeout(initialize, 100);
}

// Handle window resize
window.addEventListener('resize', () => {
  if (waveformCanvas) {
    setupCanvas();
  }
});

// Cleanup on close
window.addEventListener('beforeunload', () => {
  console.log('[Cleanup] Page unloading...');
  stopAudioCapture();
  closeSSE();
  console.log('[Cleanup] Done');
});

})(); // End IIFE
