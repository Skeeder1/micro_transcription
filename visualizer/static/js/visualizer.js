/* Visualiseur micro avancé - JavaScript - Web mode (no Qt) */

console.log('[Module] Starting independent visualizer...');

import RecordPlugin from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/record.esm.js';
console.log('[Module] RecordPlugin imported');

let wavesurfer;
let record;
let eventSource;

const micSelect = document.querySelector('#mic-select');
const statusLabel = document.querySelector('#status');
const previewText = document.querySelector('#preview-text');
const previewContainer = document.querySelector('#preview-container');
const sseStatus = document.querySelector('#sse-status');

console.log('[Module] DOM elements selected');

const showError = (msg) => {
  const errorDiv = document.querySelector('#error');
  if (errorDiv) {
    errorDiv.textContent = msg;
    console.error(msg);
  }
  if (statusLabel) {
    statusLabel.textContent = 'Error: ' + msg;
    statusLabel.style.color = '#ff6b6b';
  }
};

const setStatus = (msg) => {
  if (statusLabel) {
    statusLabel.textContent = msg;
    statusLabel.style.color = '#6bff6b';
  }
};

const updatePreview = (text) => {
  if (!text || text.trim() === '') {
    previewText.textContent = 'En attente de parole...';
    previewText.classList.add('empty');
  } else {
    previewText.textContent = text;
    previewText.classList.remove('empty');
    // Auto-scroll vers le bas
    previewContainer.scrollTop = previewContainer.scrollHeight;
  }
};

const handleStateChange = (state) => {
  const panel = document.querySelector('.panel');
  if (state === 'sleep') {
    console.log('[State] Entering sleep mode');
    panel.classList.add('sleeping');
    updatePreview('💤 Mode veille - Appuyez sur F9');
    setStatus('Mode veille');
    if (statusLabel) {
      statusLabel.style.color = '#ff9966';
    }
  } else if (state === 'active') {
    console.log('[State] Exiting sleep mode');
    panel.classList.remove('sleeping');
    updatePreview('🔊 Système réactivé - Parlez maintenant!');
    setStatus('Monitoring active - Preview ON');
    if (statusLabel) {
      statusLabel.style.color = '#6bff6b';
    }
  }
};

const connectSSE = () => {
  // Le port SSE sera injecté dynamiquement par Flask
  const ssePort = window.SSE_PORT || 5500;
  console.log(`[SSE] Connecting to http://127.0.0.1:${ssePort}/events`);

  eventSource = new EventSource(`http://127.0.0.1:${ssePort}/events`);

  eventSource.onopen = () => {
    console.log('[SSE] Connected');
    sseStatus.classList.add('connected');
    setStatus('Monitoring active - Preview ON');
  };

  eventSource.onmessage = (event) => {
    console.log('[SSE] Received:', event.data);

    // Vérifier si c'est un message d'état
    if (event.data.startsWith('STATE:')) {
      const state = event.data.substring(6); // Retirer "STATE:"
      handleStateChange(state);
    } else {
      // Message de preview normal
      updatePreview(event.data);
    }
  };

  eventSource.onerror = (error) => {
    console.error('[SSE] Error:', error);
    sseStatus.classList.remove('connected');
    setStatus('Monitoring active - Preview reconnecting...');

    // Reconnexion automatique après 2s
    setTimeout(() => {
      if (eventSource.readyState === EventSource.CLOSED) {
        console.log('[SSE] Reconnecting...');
        connectSSE();
      }
    }, 2000);
  };
};

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
    setStatus('Monitoring active - Preview ON');
  });

  record.on('record-stop', () => {
    console.log('[Recorder] Recording stopped');
    setStatus('Monitoring stopped');
  });
};

const ensureDevices = async () => {
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
    showError('Erreur accès périphériques: ' + err.message);
    return false;
  }
};

const startRecording = async () => {
  if (!record) {
    showError('Record plugin non initialisé');
    return;
  }
  if (record.isRecording()) {
    console.log('[Recorder] Already recording');
    return;
  }
  try {
    const deviceId = micSelect.value || undefined;
    console.log('[Recorder] Starting recording with deviceId:', deviceId);
    await record.startRecording({ deviceId });
    console.log('[Recorder] Recording started successfully');
  } catch (err) {
    showError('Erreur démarrage: ' + err.message);
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
  if (!record) {
    return;
  }
  if (record.isRecording()) {
    stopRecording();
  } else {
    startRecording();
  }
};

const initialize = async () => {
  try {
    console.log('[Init] Initializing visualizer...');

    if (typeof WaveSurfer === 'undefined') {
      showError('WaveSurfer non chargé');
      return;
    }
    if (typeof RecordPlugin === 'undefined') {
      showError('RecordPlugin non chargé');
      return;
    }

    console.log('[Init] WaveSurfer and RecordPlugin loaded');

    // Initialiser waveform
    createWaveSurfer();

    // Charger devices
    const hasDevice = await ensureDevices();
    if (!hasDevice) {
      showError('Aucun micro détecté');
      return;
    }

    // Démarrer enregistrement
    console.log('[Init] Starting auto-record...');
    await startRecording();

    // Connecter SSE pour preview
    connectSSE();

    console.log('[Init] Initialization complete');

  } catch (err) {
    showError('Init error: ' + err.message);
    console.error('[Init] Error:', err);
  }
};

// Bridge pour contrôle externe
window.visualizerBridge = {
  start: startRecording,
  stop: stopRecording,
  toggle: toggleRecording,
  refreshDevices: ensureDevices,
  updatePreview: updatePreview,
};

// Démarrer après chargement
if (typeof WaveSurfer !== 'undefined') {
  initialize();
} else {
  window.addEventListener('load', () => {
    setTimeout(initialize, 500);
  });
}

// Cleanup SSE à la fermeture
window.addEventListener('beforeunload', () => {
  if (eventSource) {
    eventSource.close();
  }
});
