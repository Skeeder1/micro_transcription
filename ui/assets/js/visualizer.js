/* Micro Transcription - Visualizer JavaScript */
/* WaveSurfer.js waveform + VAD/Processing indicators via SSE */

(function() {
'use strict';

console.log('[Visualizer] Starting...');

let RecordPlugin = null;
let wavesurfer = null;
let record = null;
let eventSource = null;

// DOM Elements
const panel = document.querySelector('.panel');
const recBtn = document.querySelector('#rec-btn');
const recIcon = document.querySelector('.rec-icon');
const micSelect = document.querySelector('#mic-select');
const vadIndicator = document.querySelector('#vad-indicator');
const processingIndicator = document.querySelector('#processing-indicator');
const statusLabel = document.querySelector('#status');
const previewText = document.querySelector('#preview-text');
const previewContainer = document.querySelector('#preview-container');
const sseStatus = document.querySelector('#sse-status');
const errorDiv = document.querySelector('#error');

console.log('[Visualizer] DOM elements selected');

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
    recBtn.classList.remove('rec-paused');
    recBtn.classList.add('rec-active');
    if (recIcon) recIcon.textContent = '🎤';
    recBtn.title = 'Micro actif (F8 pour pause)';
    setStatus('Micro actif', 'active');
  } else if (state === 'paused') {
    console.log('[Recording] Microphone paused');
    recBtn.classList.remove('rec-active');
    recBtn.classList.add('rec-paused');
    if (recIcon) recIcon.textContent = '⏸️';
    recBtn.title = 'Micro en pause (F8 pour reprendre)';
    setStatus('Micro en pause', 'warning');
  }
};

const handleVADChange = (state) => {
  if (!vadIndicator) return;
  if (state === 'active') {
    console.log('[VAD] Voice detected');
    vadIndicator.classList.add('active');
  } else {
    console.log('[VAD] Silence');
    vadIndicator.classList.remove('active');
  }
};

let processingTimeout = null;

const handleProcessingChange = (state) => {
  if (!processingIndicator) return;

  if (processingTimeout) {
    clearTimeout(processingTimeout);
    processingTimeout = null;
  }

  if (state === 'start') {
    console.log('[Processing] Transcription started');
    processingIndicator.classList.add('active');
    setStatus('Transcription...', 'active');
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
    setTimeout(() => {
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('[SSE] Reconnecting...');
        connectSSE();
      }
    }, 2000);
  };
};

// ===========================================
// WaveSurfer Setup
// ===========================================

const createWaveSurfer = () => {
  if (record && (record.isRecording() || record.isPaused())) {
    record.stopRecording();
  }
  if (wavesurfer) {
    try {
      wavesurfer.destroy();
    } catch (e) {
      console.warn('Error destroying wavesurfer:', e);
    }
  }

  wavesurfer = WaveSurfer.create({
    container: '#mic',
    waveColor: 'rgb(100, 200, 255)',
    progressColor: 'rgb(50, 150, 255)',
    cursorWidth: 0,
    height: 90,
    barWidth: 2,
    barGap: 1,
    barRadius: 2,
  });

  record = wavesurfer.registerPlugin(RecordPlugin.create({
    renderRecordedAudio: false,
    scrollingWaveform: true,
    continuousWaveform: false,
    scrollingWaveformWindow: 5,
  }));

  record.on('record-start', () => {
    console.log('[Recorder] Recording started');
    setStatus('Monitoring actif', 'active');
  });

  record.on('record-stop', () => {
    console.log('[Recorder] Recording stopped');
    setStatus('Monitoring arrete', 'warning');
  });
};

const ensureDevices = async () => {
  if (!micSelect) return true;
  try {
    const devices = await RecordPlugin.getAvailableAudioDevices();
    micSelect.innerHTML = '<option value="" hidden>Micro</option>';
    devices.forEach((device, index) => {
      const option = document.createElement('option');
      option.value = device.deviceId;
      option.text = device.label || device.deviceId || ('Micro ' + (index + 1));
      micSelect.appendChild(option);
    });
    if (devices.length && !micSelect.value) {
      micSelect.value = devices[0].deviceId;
    }
    console.log('[Devices] Found ' + devices.length + ' audio devices');
    return devices.length > 0;
  } catch (err) {
    showError('Erreur acces peripheriques: ' + err.message);
    return false;
  }
};

const startRecording = async () => {
  if (!record) {
    showError('Record plugin non initialise');
    return;
  }
  if (record.isRecording()) {
    console.log('[Recorder] Already recording');
    return;
  }
  try {
    const deviceId = micSelect ? micSelect.value : undefined;
    console.log('[Recorder] Starting recording with deviceId:', deviceId);
    await record.startRecording({ deviceId });
    console.log('[Recorder] Recording started successfully');
  } catch (err) {
    showError('Erreur demarrage: ' + err.message);
  }
};

const stopRecording = () => {
  if (record && record.isRecording()) {
    try {
      record.stopRecording();
    } catch (e) {
      console.warn('[Recorder] Error stopping recording:', e);
    }
  }
};

const toggleRecording = () => {
  if (!record) return;
  if (record.isRecording()) {
    stopRecording();
  } else {
    startRecording();
  }
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

    if (typeof WaveSurfer === 'undefined') {
      showError('WaveSurfer non charge');
      return;
    }

    // Get RecordPlugin from WaveSurfer global
    RecordPlugin = WaveSurfer.Record;
    if (!RecordPlugin) {
      showError('RecordPlugin non charge');
      return;
    }

    console.log('[Init] WaveSurfer and RecordPlugin loaded');

    createWaveSurfer();

    const hasDevice = await ensureDevices();
    if (!hasDevice) {
      showError('Aucun micro detecte');
      return;
    }

    console.log('[Init] Starting auto-record...');
    await startRecording();

    connectSSE();

    console.log('[Init] Initialization complete');

  } catch (err) {
    showError('Init error: ' + err.message);
    console.error('[Init] Error:', err);
  }
};

// ===========================================
// Bridge for External Control
// ===========================================

window.visualizerBridge = {
  start: startRecording,
  stop: stopRecording,
  toggle: toggleRecording,
  refreshDevices: ensureDevices,
  updatePreview: updatePreview,
};

// ===========================================
// Start
// ===========================================

if (typeof WaveSurfer !== 'undefined') {
  initialize();
} else {
  window.addEventListener('load', () => {
    setTimeout(initialize, 500);
  });
}

window.addEventListener('beforeunload', () => {
  if (eventSource) {
    eventSource.close();
  }
});

})(); // End IIFE
