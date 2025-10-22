"""Visualizer avancé avec affichage preview temps réel via SSE.

Reçoit le texte preview depuis main_enhanced.py via Server-Sent Events
et l'affiche sous la forme d'onde pour feedback utilisateur immédiat.
"""

from __future__ import annotations

import sys

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


def get_html_template(sse_port: int) -> str:
    """Génère le template HTML avec EventSource configuré."""
    return f"""<!DOCTYPE html>
<html lang='fr'>
<head>
<meta charset='utf-8'>
<title>Visualiseur micro avancé</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ background:#222; margin:0; display:flex; height:100vh; align-items:center; justify-content:center; font-family:Arial, sans-serif; }}
  .panel {{ width:580px; background:#2b2b2b; border-radius:12px; padding:14px 18px 12px; box-shadow:0 10px 30px rgba(0,0,0,.35); position:relative; color:#ddd; }}
  
  /* Waveform */
  #mic {{ height:90px; border-radius:6px; overflow:hidden; background:#1a1a1a; transition: opacity 0.3s; }}
  
  /* Sleep mode overlay */
  .panel.sleeping #mic {{ opacity: 0.2; }}
  .panel.sleeping {{ background:#1a1a1a; }}
  
  /* Toolbar */
  .toolbar {{ display:flex; gap:8px; align-items:center; margin-bottom:6px; }}
  select {{ background:#3a3a3a; color:#f2f2f2; border:0; padding:4px 8px; border-radius:4px; font-size:11px; }}
  #status {{ margin:2px 0 0; font-size:10px; color:#999; }}
  
  /* Preview text zone */
  #preview-container {{
    margin-top: 10px;
    max-height: 60px;
    overflow-y: auto;
    padding: 8px;
    background: #1a1a1a;
    border-radius: 6px;
    font-size: 11px;
    line-height: 1.4;
    color: #999;
    font-style: italic;
    transition: opacity 0.2s;
  }}
  #preview-text {{
    margin: 0;
    word-wrap: break-word;
    animation: fadeIn 0.2s;
  }}
  #preview-text.empty {{
    opacity: 0.3;
  }}
  
  /* Scrollbar styling */
  #preview-container::-webkit-scrollbar {{
    width: 6px;
  }}
  #preview-container::-webkit-scrollbar-track {{
    background: #2b2b2b;
    border-radius: 3px;
  }}
  #preview-container::-webkit-scrollbar-thumb {{
    background: #3a3a3a;
    border-radius: 3px;
  }}
  #preview-container::-webkit-scrollbar-thumb:hover {{
    background: #4a4a4a;
  }}
  
  /* SSE status indicator */
  #sse-status {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #666;
    margin-left: 8px;
    transition: background 0.3s;
  }}
  #sse-status.connected {{
    background: #6bff6b;
    box-shadow: 0 0 8px #6bff6b;
  }}
  
  #error {{ color:#ff6b6b; margin-top:6px; font-size:11px; }}
  
  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(-5px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}
</style>
</head>
<body>
  <div class='panel'>
    <div class='toolbar'>
      <select id='mic-select'><option value='' hidden>Sélection micro</option></select>
      <span id='status'>Monitoring...</span>
      <span id='sse-status' title='SSE connection'></span>
    </div>
    
    <div id='mic' style='margin-top:12px;'></div>
    
    <div id='preview-container'>
      <div id='preview-text' class='empty'>En attente de parole...</div>
    </div>
    
    <div id='error'></div>
  </div>

  <script src='https://unpkg.com/wavesurfer.js@7'></script>
  <script src='qrc:///qtwebchannel/qwebchannel.js'></script>
  <script type='module'>
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
    
    console.log('[Module] DOM elements selected');

    const showError = (msg) => {{
      const errorDiv = document.querySelector('#error');
      if (errorDiv) {{
        errorDiv.textContent = msg;
        console.error(msg);
      }}
      if (statusLabel) {{
        statusLabel.textContent = 'Error: ' + msg;
        statusLabel.style.color = '#ff6b6b';
      }}
    }};

    const setStatus = (msg) => {{
      if (statusLabel) {{
        statusLabel.textContent = msg;
        statusLabel.style.color = '#6bff6b';
      }}
    }};

    const updatePreview = (text) => {{
      if (!text || text.trim() === '') {{
        previewText.textContent = 'En attente de parole...';
        previewText.classList.add('empty');
      }} else {{
        previewText.textContent = text;
        previewText.classList.remove('empty');
        // Auto-scroll vers le bas
        previewContainer.scrollTop = previewContainer.scrollHeight;
      }}
    }};
    
    const handleStateChange = (state) => {{
      const panel = document.querySelector('.panel');
      if (state === 'sleep') {{
        console.log('[State] Entering sleep mode - hiding window');
        panel.classList.add('sleeping');
        updatePreview('💤 Mode veille - Appuyez sur F9');
        setStatus('Mode veille');
        if (statusLabel) {{
          statusLabel.style.color = '#ff9966';
        }}
        // Appeler Qt pour masquer la fenêtre
        if (window.qtBridge) {{
          window.qtBridge.handleStateChange('sleep');
        }}
      }} else if (state === 'active') {{
        console.log('[State] Exiting sleep mode - showing window');
        panel.classList.remove('sleeping');
        updatePreview('🔊 Système réactivé - Parlez maintenant!');
        setStatus('Monitoring active - Preview ON');
        if (statusLabel) {{
          statusLabel.style.color = '#6bff6b';
        }}
        // Appeler Qt pour afficher la fenêtre
        if (window.qtBridge) {{
          window.qtBridge.handleStateChange('active');
        }}
      }}
    }};

    const connectSSE = () => {{
      console.log('[SSE] Connecting to http://127.0.0.1:{sse_port}/events');
      
      eventSource = new EventSource('http://127.0.0.1:{sse_port}/events');
      
      eventSource.onopen = () => {{
        console.log('[SSE] Connected');
        sseStatus.classList.add('connected');
        setStatus('Monitoring active - Preview ON');
      }};
      
      eventSource.onmessage = (event) => {{
        console.log('[SSE] Received:', event.data);
        
        // Vérifier si c'est un message d'état
        if (event.data.startsWith('STATE:')) {{
          const state = event.data.substring(6); // Retirer "STATE:"
          handleStateChange(state);
        }} else {{
          // Message de preview normal
          updatePreview(event.data);
        }}
      }};
      
      eventSource.onerror = (error) => {{
        console.error('[SSE] Error:', error);
        sseStatus.classList.remove('connected');
        setStatus('Monitoring active - Preview reconnecting...');
        
        // Reconnexion automatique après 2s
        setTimeout(() => {{
          if (eventSource.readyState === EventSource.CLOSED) {{
            console.log('[SSE] Reconnecting...');
            connectSSE();
          }}
        }}, 2000);
      }};
    }};

    const createWaveSurfer = () => {{
      if (record && (record.isRecording() || record.isPaused())) {{
        record.stopRecording();
      }}
      if (wavesurfer) {{
        try {{
          wavesurfer.destroy();
        }} catch (e) {{
          console.warn('Error destroying wavesurfer:', e);
        }}
      }}

      wavesurfer = WaveSurfer.create({{
        container: '#mic',
        waveColor: 'rgb(100, 200, 255)',
        progressColor: 'rgb(50, 150, 255)',
        cursorWidth: 0,
        height: 90,
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
      }});

      record = wavesurfer.registerPlugin(RecordPlugin.create({{
        renderRecordedAudio: false,
        scrollingWaveform: true,
        continuousWaveform: false,
        scrollingWaveformWindow: 5,
      }}));

      record.on('record-start', () => {{
        console.log('[Recorder] Recording started');
        setStatus('Monitoring active - Preview ON');
      }});

      record.on('record-stop', () => {{
        console.log('[Recorder] Recording stopped');
        setStatus('Monitoring stopped');
      }});
    }};

    const ensureDevices = async () => {{
      try {{
        const devices = await RecordPlugin.getAvailableAudioDevices();
        micSelect.innerHTML = '<option value="" hidden>Micro</option>';
        devices.forEach((device, index) => {{
          const option = document.createElement('option');
          option.value = device.deviceId;
          option.text = device.label || device.deviceId || ('Micro ' + (index + 1));
          micSelect.appendChild(option);
        }});
        if (devices.length && !micSelect.value) {{
          micSelect.value = devices[0].deviceId;
        }}
        console.log('[Devices] Found ' + devices.length + ' audio devices');
        return devices.length > 0;
      }} catch (err) {{
        showError('Erreur accès périphériques: ' + err.message);
        return false;
      }}
    }};

    const startRecording = async () => {{
      if (!record) {{
        showError('Record plugin non initialisé');
        return;
      }}
      if (record.isRecording()) {{
        console.log('[Recorder] Already recording');
        return;
      }}
      try {{
        const deviceId = micSelect.value || undefined;
        console.log('[Recorder] Starting recording with deviceId:', deviceId);
        await record.startRecording({{ deviceId }});
        console.log('[Recorder] Recording started successfully');
      }} catch (err) {{
        showError('Erreur démarrage: ' + err.message);
      }}
    }};

    const stopRecording = () => {{
      if (record && record.isRecording()) {{
        try {{
          record.stopRecording();
        }} catch (e) {{
          console.warn('[Recorder] Error stopping recording:', e);
        }}
      }}
    }};

    const toggleRecording = () => {{
      if (!record) {{
        return;
      }}
      if (record.isRecording()) {{
        stopRecording();
      }} else {{
        startRecording();
      }}
    }};

    const initialize = async () => {{
      try {{
        console.log('[Init] Initializing visualizer...');
        
        // Initialiser Qt WebChannel
        if (typeof QWebChannel !== 'undefined' && window.qt && window.qt.webChannelTransport) {{
          new QWebChannel(window.qt.webChannelTransport, function(channel) {{
            window.qtBridge = channel.objects.qtBridge;
            console.log('[Init] Qt WebChannel initialized');
          }});
        }} else {{
          console.warn('[Init] Qt WebChannel not available');
        }}
        
        if (typeof WaveSurfer === 'undefined') {{
          showError('WaveSurfer non chargé');
          return;
        }}
        if (typeof RecordPlugin === 'undefined') {{
          showError('RecordPlugin non chargé');
          return;
        }}
        
        console.log('[Init] WaveSurfer and RecordPlugin loaded');
        
        // Initialiser waveform
        createWaveSurfer();
        
        // Charger devices
        const hasDevice = await ensureDevices();
        if (!hasDevice) {{
          showError('Aucun micro détecté');
          return;
        }}
        
        // Démarrer enregistrement
        console.log('[Init] Starting auto-record...');
        await startRecording();
        
        // Connecter SSE pour preview
        connectSSE();
        
        console.log('[Init] Initialization complete');
        
      }} catch (err) {{
        showError('Init error: ' + err.message);
        console.error('[Init] Error:', err);
      }}
    }};

    // Bridge pour contrôle externe
    window.visualizerBridge = {{
      start: startRecording,
      stop: stopRecording,
      toggle: toggleRecording,
      refreshDevices: ensureDevices,
      updatePreview: updatePreview,
    }};

    // Démarrer après chargement
    if (typeof WaveSurfer !== 'undefined') {{
      initialize();
    }} else {{
      window.addEventListener('load', () => {{
        setTimeout(initialize, 500);
      }});
    }}
    
    // Cleanup SSE à la fermeture
    window.addEventListener('beforeunload', () => {{
      if (eventSource) {{
        eventSource.close();
      }}
    }});
  </script>
</body>
</html>
"""


class VisualizerEnhanced(QtWidgets.QMainWindow):
    def __init__(self, sse_port: int = 5432) -> None:
        super().__init__()
        self.setWindowTitle("Micro Monitor - Enhanced")
        self.resize(600, 200)  # Hauteur augmentée pour preview text
        
        # Positionner la fenêtre en haut au milieu de l'écran
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen.width() - 600) // 2  # Centrer horizontalement
        y = 20  # 20 pixels depuis le haut
        self.move(x, y)
        
        # CORRECTIF: Empêcher la fenêtre de prendre le focus
        # Cela évite que Alt reste bloquée quand on lance le visualizer avec Alt+W
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self._view = QWebEngineView()
        self._view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self._view.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)  # Aussi pour la webview
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # Page custom pour logs
        class DebugPage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                _ = level, sourceID  # Unused but required by signature
                print(f"[JS] {message} (line {lineNumber})")
        
        page = DebugPage(self._view)
        self._view.setPage(page)
        page.featurePermissionRequested.connect(self._on_feature_permission_requested)
        self._view.loadFinished.connect(self._on_load_finished)
        
        # Charger HTML avec port SSE
        html = get_html_template(sse_port)
        self._view.setHtml(html, baseUrl=QtCore.QUrl("https://visualizer.local/"))
        self.setCentralWidget(self._view)

        self._always_on_top = True
        self._paused = False
        self._is_hidden_for_sleep = False  # Track si caché pour veille
        self._apply_window_flags()
        
        # Setup bridge Qt pour communication JS -> Python
        self._setup_qt_bridge()

    def _on_feature_permission_requested(self, origin: QtCore.QUrl, feature: QWebEnginePage.Feature) -> None:
        print(f"[Permission] Feature requested: {feature}")
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            if feature == QWebEnginePage.Feature.MediaAudioCapture:
                print("[Permission] Granting MediaAudioCapture")
                self._view.page().setFeaturePermission(
                    origin,
                    feature,
                    QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
                )
            else:
                print(f"[Permission] Denying feature: {feature}")
                self._view.page().setFeaturePermission(
                    origin,
                    feature,
                    QWebEnginePage.PermissionPolicy.PermissionDeniedByUser
                )

    def _on_load_finished(self, ok: bool) -> None:
        print(f"[Load] Page loaded: {ok}")
        if ok and not self._paused:
            print("[Load] Starting visualizer bridge...")
            self._invoke_js("window.visualizerBridge && window.visualizerBridge.start();")
    
    def _setup_qt_bridge(self) -> None:
        """Setup Qt WebChannel pour communication bidirectionnelle JS <-> Python."""
        from PySide6.QtWebChannel import QWebChannel
        
        class Bridge(QtCore.QObject):
            def __init__(self, parent_window):
                super().__init__()
                self.parent_window = parent_window
            
            @QtCore.Slot(str)
            def handleStateChange(self, state: str):
                """Appelé depuis JS quand l'état change."""
                print(f"[Bridge] State change received: {state}")
                if state == "sleep":
                    print("[Bridge] Hiding window for sleep mode")
                    self.parent_window._is_hidden_for_sleep = True
                    self.parent_window.hide()
                elif state == "active":
                    print("[Bridge] Showing window for active mode")
                    self.parent_window._is_hidden_for_sleep = False
                    self.parent_window.show()
        
        self._bridge = Bridge(self)
        self._channel = QWebChannel()
        self._channel.registerObject("qtBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key = event.key()
        if key == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif key == QtCore.Qt.Key.Key_Space:
            self._paused = not self._paused
            self._invoke_js("window.visualizerBridge && window.visualizerBridge.toggle();")
        elif key == QtCore.Qt.Key.Key_T:
            self._always_on_top = not self._always_on_top
            self._apply_window_flags()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        try:
            self._invoke_js("window.visualizerBridge && window.visualizerBridge.stop();")
            QtCore.QTimer.singleShot(100, lambda: None)
        except (RuntimeError, AttributeError) as e:
            print(f"[Close] Error: {e}")
        super().closeEvent(event)

    def _invoke_js(self, script: str) -> None:
        self._view.page().runJavaScript(script)

    def _apply_window_flags(self) -> None:
        flags = self.windowFlags()
        
        # Toujours empêcher la prise de focus (même si clics sur la fenêtre)
        flags |= QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        
        if self._always_on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowType.WindowStaysOnTopHint
        
        self.setWindowFlags(flags)
        self.show()


def main() -> None:
    # Port SSE passé en argument
    sse_port = int(sys.argv[1]) if len(sys.argv) > 1 else 5432
    
    app = QtWidgets.QApplication(sys.argv)
    visualizer = VisualizerEnhanced(sse_port=sse_port)
    visualizer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
