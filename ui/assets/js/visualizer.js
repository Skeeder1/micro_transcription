/* Micro Transcription - Visualizer JavaScript */
/* 60 FPS waveform with local audio + VAD coloring from backend SSE */

console.log('[Module] Starting visualizer...');

let eventSource;
let animationId = null;
let audioContext = null;
let analyser = null;
let audioStream = null;

// VAD state from backend SSE (colors the waveform)
let isVoiceActive = false;

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
// Waveform History (scrolling effect)
// ===========================================

const HISTORY_LENGTH = 200;  // Number of bars in history
let waveformHistory = [];

// Initialize history with empty values
for (let i = 0; i < HISTORY_LENGTH; i++) {
  waveformHistory.push({ rms: 0, voice: false });
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
    updatePreview('Mode veille - Appuyez sur F9');
    setStatus('Mode veille', 'warning');

    // Notify Qt to hide window
    if (window.qtBridge) {
      window.qtBridge.handleStateChange('sleep');
    }
  } else if (state === 'active') {
    console.log('[State] Exiting sleep mode');
    panel.classList.remove('sleeping');
    updatePreview('Systeme active - Parlez maintenant!');
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
    isVoiceActive = true;
  } else {
    console.log('[VAD] Silence');
    vadIndicator.classList.remove('active');
    isVoiceActive = false;
  }
};

// Timeout de securite pour le processing (30s max)
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
// SSE Connection
// ===========================================

const connectSSE = () => {
  const ssePort = window.SSE_PORT || 5432;
  console.log(`[SSE] Connecting to http://127.0.0.1:${ssePort}/events`);

  eventSource = new EventSource(`http://127.0.0.1:${ssePort}/events`);

  eventSource.onopen = () => {
    console.log('[SSE] Connected');
    sseStatus.classList.add('connected');
    setStatus('Connecte', 'active');
  };

  eventSource.onmessage = (event) => {
    // Parse message type
    if (event.data.startsWith('STATE:')) {
      console.log('[SSE] Received:', event.data);
      const state = event.data.substring(6);
      handleStateChange(state);
    } else if (event.data.startsWith('RECORDING:')) {
      console.log('[SSE] Received:', event.data);
      const state = event.data.substring(10);
      handleRecordingChange(state);
    } else if (event.data.startsWith('VAD:')) {
      // VAD updates are frequent - no logging
      const state = event.data.substring(4);
      handleVADChange(state);
    } else if (event.data.startsWith('PROCESSING:')) {
      console.log('[SSE] Received:', event.data);
      const state = event.data.substring(11);
      handleProcessingChange(state);
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
// Web Audio API Setup
// ===========================================

const setupAudio = async () => {
  try {
    console.log('[Audio] Requesting microphone access...');

    // Request microphone with specific constraints
    audioStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: true  // Let browser normalize volume
      }
    });

    console.log('[Audio] Microphone access granted');

    // Create audio context
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const source = audioContext.createMediaStreamSource(audioStream);

    // Highpass filter at 80Hz (removes rumble/low frequency noise)
    const highpass = audioContext.createBiquadFilter();
    highpass.type = 'highpass';
    highpass.frequency.value = 80;
    highpass.Q.value = 0.7;

    // Compressor for automatic volume normalization
    // This makes quiet voices visible and prevents clipping
    const compressor = audioContext.createDynamicsCompressor();
    compressor.threshold.value = -50;  // Start compressing at -50dB
    compressor.knee.value = 40;        // Soft knee for natural sound
    compressor.ratio.value = 12;       // High ratio = more normalization
    compressor.attack.value = 0;       // Instant attack
    compressor.release.value = 0.25;   // 250ms release

    // Analyser for waveform data
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;  // 128 frequency bins
    analyser.smoothingTimeConstant = 0.3;  // Some smoothing

    // Connect the audio pipeline
    source.connect(highpass);
    highpass.connect(compressor);
    compressor.connect(analyser);
    // Note: not connecting to destination (no playback)

    console.log('[Audio] Audio pipeline initialized');
    return true;

  } catch (err) {
    console.error('[Audio] Error:', err);
    showError('Erreur micro: ' + err.message);
    return false;
  }
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
  if (!waveformCanvas || !analyser) {
    animationId = requestAnimationFrame(drawWaveform);
    return;
  }

  const ctx = waveformCanvas.getContext('2d');
  const width = waveformCanvas.width;
  const height = waveformCanvas.height;

  // Get current audio data
  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteTimeDomainData(dataArray);

  // Calculate RMS from waveform data
  let sum = 0;
  for (let i = 0; i < dataArray.length; i++) {
    const normalized = (dataArray[i] - 128) / 128;  // -1 to 1
    sum += normalized * normalized;
  }
  const rms = Math.sqrt(sum / dataArray.length);

  // Apply power curve to make quiet sounds more visible
  const amplified = Math.pow(rms, 0.6) * 2.5;

  // Add current sample to history with current VAD state
  waveformHistory.shift();
  waveformHistory.push({ rms: amplified, voice: isVoiceActive });

  // Clear canvas
  ctx.fillStyle = '#1a1a1a';  // --bg-primary
  ctx.fillRect(0, 0, width, height);

  // Draw waveform bars from history
  const barWidth = width / HISTORY_LENGTH;
  const barGap = 1 * window.devicePixelRatio;
  const actualBarWidth = Math.max(barWidth - barGap, 2);

  for (let i = 0; i < HISTORY_LENGTH; i++) {
    const data = waveformHistory[i];

    // Calculate bar height (minimum 2px for visibility)
    const barHeight = Math.max(data.rms * height * 0.9, 2 * window.devicePixelRatio);

    // Position bar centered vertically
    const x = i * barWidth;
    const y = (height - barHeight) / 2;

    // Color based on VAD state from backend
    if (data.voice) {
      // Voice detected - green gradient
      const intensity = Math.min(data.rms * 1.5, 1);
      const r = Math.floor(74 + intensity * 50);   // 74 -> 124
      const g = Math.floor(222 - intensity * 30);  // 222 -> 192
      const b = Math.floor(128 - intensity * 50);  // 128 -> 78
      ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
    } else {
      // Silence/noise - blue gradient
      const intensity = Math.min(data.rms * 1.5, 1);
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

  // Continue animation at 60 FPS
  animationId = requestAnimationFrame(drawWaveform);
};

// ===========================================
// Initialization
// ===========================================

const initialize = async () => {
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

  // Setup audio (getUserMedia + Web Audio API)
  const audioReady = await setupAudio();
  if (!audioReady) {
    console.error('[Init] Audio setup failed');
    // Continue anyway - waveform will show flat line
  }

  // Start waveform animation (60 FPS)
  console.log('[Init] Starting waveform animation...');
  drawWaveform();

  // Connect SSE for VAD and other events
  connectSSE();

  console.log('[Init] Initialization complete');
};

// ===========================================
// Bridge for External Control
// ===========================================

window.visualizerBridge = {
  updatePreview: updatePreview,
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

  // Stop audio
  if (audioStream) {
    audioStream.getTracks().forEach(track => track.stop());
  }
  if (audioContext) {
    audioContext.close();
  }

  // Close SSE
  if (eventSource) {
    eventSource.close();
  }

  console.log('[Cleanup] Done');
});
