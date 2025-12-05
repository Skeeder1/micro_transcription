/* Micro Transcription - Visualizer JavaScript */
/* Waveform data received via SSE from preprocessed backend audio */

console.log('[Module] Starting visualizer...');

let eventSource;
let animationId = null;

// DOM Elements
const panel = document.querySelector('.panel');
const recBtn = document.querySelector('#rec-btn');
const recIcon = document.querySelector('.rec-icon');
const vadIndicator = document.querySelector('#vad-indicator');
const processingIndicator = document.querySelector('#processing-indicator');
const statusLabel = document.querySelector('#status');
const previewText = document.querySelector('#preview-text');
const previewContainer = document.querySelector('#preview-container');
const sseStatus = document.querySelector('#sse-status');
const errorDiv = document.querySelector('#error');
const waveformCanvas = document.querySelector('#waveform-canvas');

console.log('[Module] DOM elements selected');

// ===========================================
// Waveform Data (received via SSE)
// ===========================================

const HISTORY_LENGTH = 200;  // Number of bars in history
let waveformHistory = [];

// Initialize history with empty values
for (let i = 0; i < HISTORY_LENGTH; i++) {
  waveformHistory.push({ rms: 0, peak: 0, voice: false });
}

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
  if (!text || text.trim() === '') {
    previewText.textContent = 'En attente de parole...';
    previewText.classList.add('empty');
    previewContainer.classList.remove('has-text');
  } else {
    previewText.textContent = text;
    previewText.classList.remove('empty');
    previewContainer.classList.add('has-text');
    // Auto-scroll to bottom
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
    updatePreview('💤 Mode veille - Appuyez sur F9');
    setStatus('Mode veille', 'warning');

    // Notify Qt to hide window
    if (window.qtBridge) {
      window.qtBridge.handleStateChange('sleep');
    }
  } else if (state === 'active') {
    console.log('[State] Exiting sleep mode');
    panel.classList.remove('sleeping');
    updatePreview('🔊 Système activé - Parlez maintenant!');
    setStatus('Actif', 'active');

    // Notify Qt to show window
    if (window.qtBridge) {
      window.qtBridge.handleStateChange('active');
    }
  }
};

const handleRecordingChange = (state) => {
  if (state === 'recording') {
    console.log('[Recording] Microphone active');
    recBtn.classList.remove('rec-paused');
    recBtn.classList.add('rec-active');
    recIcon.textContent = '🎤';
    recBtn.title = 'Micro actif (F8 pour pause)';
    setStatus('Micro actif', 'active');
  } else if (state === 'paused') {
    console.log('[Recording] Microphone paused');
    recBtn.classList.remove('rec-active');
    recBtn.classList.add('rec-paused');
    recIcon.textContent = '⏸️';
    recBtn.title = 'Micro en pause (F8 pour reprendre)';
    setStatus('Micro en pause', 'warning');
  }
};

const handleVADChange = (state) => {
  if (state === 'active') {
    console.log('[VAD] Voice detected');
    vadIndicator.classList.add('active');
  } else {
    console.log('[VAD] Silence');
    vadIndicator.classList.remove('active');
  }
};

// Timeout de sécurité pour le processing (30s max)
let processingTimeout = null;

const handleProcessingChange = (state) => {
  // Clear any existing timeout
  if (processingTimeout) {
    clearTimeout(processingTimeout);
    processingTimeout = null;
  }

  if (state === 'start') {
    console.log('[Processing] Transcription started');
    processingIndicator.classList.add('active');
    setStatus('Transcription...', 'active');

    // Safety timeout: reset after 30s if no 'done' received
    processingTimeout = setTimeout(() => {
      console.warn('[Processing] Timeout - forcing reset');
      processingIndicator.classList.remove('active');
      setStatus('Actif', 'active');
    }, 30000);

  } else if (state === 'done') {
    console.log('[Processing] Transcription complete');
    processingIndicator.classList.remove('active');
    setStatus('Actif', 'active');
  }
};

// ===========================================
// Waveform Data Handler (from SSE)
// ===========================================

const handleWaveformData = (rms, peak, isVoice) => {
  // Shift history left and add new value at end
  waveformHistory.shift();
  waveformHistory.push({ rms, peak, voice: isVoice });
};

// ===========================================
// SSE Connection
// ===========================================

const connectSSE = () => {
  const ssePort = window.SSE_PORT || 5432;
  console.log(`[SSE] Connecting to http://127.0.0.1:${ssePort}/events`);

  eventSource = new EventSource(`http://127.0.0.1:${ssePort}/events`);

  eventSource.onopen = () => {
    console.log('[SSE] Connected');
    sseStatus.classList.add('connected');
    setStatus('Connecté', 'active');
  };

  eventSource.onmessage = (event) => {
    // Parse message type (don't log WAVEFORM to avoid spam)
    if (event.data.startsWith('STATE:')) {
      console.log('[SSE] Received:', event.data);
      const state = event.data.substring(6);
      handleStateChange(state);
    } else if (event.data.startsWith('RECORDING:')) {
      console.log('[SSE] Received:', event.data);
      const state = event.data.substring(10);
      handleRecordingChange(state);
    } else if (event.data.startsWith('VAD:')) {
      console.log('[SSE] Received:', event.data);
      const state = event.data.substring(4);
      handleVADChange(state);
    } else if (event.data.startsWith('PROCESSING:')) {
      console.log('[SSE] Received:', event.data);
      const state = event.data.substring(11);
      handleProcessingChange(state);
    } else if (event.data.startsWith('WAVEFORM:')) {
      // WAVEFORM:rms,peak,isVoice - high frequency, no logging
      const parts = event.data.substring(9).split(',');
      const rms = parseFloat(parts[0]);
      const peak = parseFloat(parts[1]);
      const isVoice = parts[2] === '1';
      handleWaveformData(rms, peak, isVoice);
    } else {
      // Regular preview message
      console.log('[SSE] Received:', event.data);
      updatePreview(event.data);
    }
  };

  eventSource.onerror = (error) => {
    console.error('[SSE] Error:', error);
    sseStatus.classList.remove('connected');
    setStatus('Reconnexion...', 'warning');

    // Auto-reconnect after 2s
    setTimeout(() => {
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('[SSE] Reconnecting...');
        connectSSE();
      }
    }, 2000);
  };
};

// ===========================================
// Canvas Waveform Visualization
// ===========================================

const setupCanvas = () => {
  if (!waveformCanvas) {
    console.error('[Canvas] Canvas element not found!');
    return false;
  }

  // Set actual canvas dimensions (not just CSS)
  const rect = waveformCanvas.getBoundingClientRect();
  waveformCanvas.width = rect.width * window.devicePixelRatio;
  waveformCanvas.height = rect.height * window.devicePixelRatio;

  console.log('[Canvas] Initialized:', waveformCanvas.width, 'x', waveformCanvas.height);
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

  // Clear canvas
  ctx.fillStyle = '#1a1a1a';  // --bg-primary
  ctx.fillRect(0, 0, width, height);

  // Draw waveform bars from SSE history
  const barWidth = width / HISTORY_LENGTH;
  const barGap = 1 * window.devicePixelRatio;
  const actualBarWidth = Math.max(barWidth - barGap, 2);

  for (let i = 0; i < HISTORY_LENGTH; i++) {
    const data = waveformHistory[i];

    // Height based on RMS, amplified for visibility
    // Apply power curve to make quiet sounds more visible
    const amplified = Math.pow(data.rms, 0.6) * 2.5;

    // Calculate bar height (minimum 2px for visibility)
    const barHeight = Math.max(amplified * height * 0.9, 2 * window.devicePixelRatio);

    // Position bar centered vertically
    const x = i * barWidth;
    const y = (height - barHeight) / 2;

    // Color based on voice detection
    if (data.voice) {
      // Voice detected - green gradient
      const intensity = Math.min(data.rms * 3, 1);
      const r = Math.floor(74 + intensity * 50);   // 74 -> 124
      const g = Math.floor(222 - intensity * 30);  // 222 -> 192
      const b = Math.floor(128 - intensity * 50);  // 128 -> 78
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
    } else {
      // Silence/noise - blue gradient
      const intensity = Math.min(data.rms * 3, 1);
      const r = Math.floor(100 + intensity * 50);  // 100 -> 150
      const g = Math.floor(180 + intensity * 20);  // 180 -> 200
      const b = Math.floor(255 - intensity * 30);  // 255 -> 225
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
    }

    // Draw rounded bar
    ctx.beginPath();
    const radius = Math.min(actualBarWidth / 2, 3 * window.devicePixelRatio);
    ctx.roundRect(x, y, actualBarWidth, barHeight, radius);
    ctx.fill();
  }

  // Continue animation
  animationId = requestAnimationFrame(drawWaveform);
};

// ===========================================
// Initialization
// ===========================================

const initialize = () => {
  console.log('[Init] Initializing visualizer...');

  // Initialize Qt WebChannel
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
    console.error('[Init] Canvas setup failed, retrying...');
    setTimeout(initialize, 500);
    return;
  }

  // Start waveform animation (data comes via SSE)
  console.log('[Init] Starting waveform animation...');
  drawWaveform();

  // Connect SSE for all data (including waveform)
  connectSSE();

  console.log('[Init] Initialization complete');
};

// ===========================================
// Bridge for External Control
// ===========================================

window.visualizerBridge = {
  updatePreview: updatePreview,
  // No more start/stop needed - waveform data comes via SSE
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

  // Cancel animation
  if (animationId) {
    cancelAnimationFrame(animationId);
    animationId = null;
  }

  // Close SSE
  if (eventSource) {
    eventSource.close();
  }

  console.log('[Cleanup] Done');
});
