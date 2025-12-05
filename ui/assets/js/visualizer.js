/* Visualiseur micro avancé - JavaScript */

console.log('[Module] Starting enhanced visualizer...');

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
const recBtn = document.querySelector('#rec-btn');

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
    console.log('[State] Entering sleep mode - hiding window');
    panel.classList.add('sleeping');
    updatePreview('💤 Mode veille - Appuyez sur F9');
    setStatus('Mode veille');
    if (statusLabel) {
      statusLabel.style.color = '#ff9966';
    }
    // Appeler Qt pour masquer la fenêtre
    if (window.qtBridge) {
      window.qtBridge.handleStateChange('sleep');
    }
  } else if (state === 'active') {
    console.log('[State] Exiting sleep mode - showing window');
    panel.classList.remove('sleeping');
    updatePreview('🔊 Système réactivé - Parlez maintenant!');
    setStatus('Monitoring active - Preview ON');
    if (statusLabel) {
      statusLabel.style.color = '#6bff6b';
    }
    // Appeler Qt pour afficher la fenêtre
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
    recBtn.textContent = '🎤';
    recBtn.title = 'Enregistrement actif (F8 pour pause)';
    setStatus('🎤 Enregistrement actif');
    if (statusLabel) {
      statusLabel.style.color = '#6bff6b';
    }
  } else if (state === 'paused') {
    console.log('[Recording] Microphone paused');
    recBtn.classList.remove('rec-active');
    recBtn.classList.add('rec-paused');
    recBtn.textContent = '⏸️';
    recBtn.title = 'Enregistrement en pause (F8 pour reprendre)';
    setStatus('⏸️ Enregistrement en pause');
    if (statusLabel) {
      statusLabel.style.color = '#ff9966';
    }
  }
};

const connectSSE = () => {
  // Le port SSE sera injecté dynamiquement par Python
  const ssePort = window.SSE_PORT || 5432;
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
    } else if (event.data.startsWith('RECORDING:')) {
      const state = event.data.substring(10); // Retirer "RECORDING:"
      handleRecordingChange(state);
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

    // Initialiser Qt WebChannel
    if (typeof QWebChannel !== 'undefined' && window.qt && window.qt.webChannelTransport) {
      new QWebChannel(window.qt.webChannelTransport, function(channel) {
        window.qtBridge = channel.objects.qtBridge;
        console.log('[Init] Qt WebChannel initialized');
      });
    } else {
      console.warn('[Init] Qt WebChannel not available');
    }

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
