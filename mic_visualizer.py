"""Microphone visualizer embedding a Wavesurfer.js recorder UI via Qt WebEngine.

Install dependencies:
    pip install --upgrade pip
    pip install PySide6 pyqtgraph sounddevice numpy
"""

from __future__ import annotations

import sys

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang='fr'>
<head>
<meta charset='utf-8'>
<title>Visualiseur micro</title>
<style>
  :root { color-scheme: dark; }
  body { background:#222; margin:0; display:flex; height:100vh; align-items:center; justify-content:center; font-family:Arial, sans-serif; }
  .panel { width:900px; background:#2b2b2b; border-radius:16px; padding:24px 28px 20px; box-shadow:0 10px 30px rgba(0,0,0,.35); position:relative; color:#ddd; }
  #mic { height:120px; border-radius:8px; overflow:hidden; background:#1a1a1a; }
  .toolbar { display:flex; gap:10px; align-items:center; margin-bottom:8px; }
  select { background:#3a3a3a; color:#f2f2f2; border:0; padding:6px 10px; border-radius:6px; }
  #status { margin:4px 0 0; font-size:12px; color:#999; }
  #error { color:#ff6b6b; margin-top:8px; font-size:13px; }
</style>
</head>
<body>
  <div class='panel'>
    <div class='toolbar'>
      <select id='mic-select'><option value='' hidden>Sélection micro</option></select>
      <span id='status'>Monitoring...</span>
    </div>
    <div id='mic' style='margin-top:12px;'></div>
    <div id='error'></div>
  </div>

  <script src='https://unpkg.com/wavesurfer.js@7'></script>
  <script type='module'>
    console.log('[Module] Starting ES module...');
    
    // Import du plugin Record depuis le module ES
    import RecordPlugin from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/record.esm.js';
    console.log('[Module] RecordPlugin imported');
    
    let wavesurfer;
    let record;

    const micSelect = document.querySelector('#mic-select');
    const statusLabel = document.querySelector('#status');
    
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
        height: 120,
      });

      record = wavesurfer.registerPlugin(RecordPlugin.create({
        renderRecordedAudio: false,
        scrollingWaveform: true,
        continuousWaveform: false,
      }));

      record.on('record-start', () => {
        console.log('Recording started');
        setStatus('Monitoring active');
      });

      record.on('record-stop', () => {
        console.log('Recording stopped');
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
        console.log('Found ' + devices.length + ' audio devices');
        setStatus('Ready - ' + devices.length + ' device(s)');
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
        console.log('Already recording');
        return;
      }
      try {
        const deviceId = micSelect.value || undefined;
        console.log('Starting recording with deviceId:', deviceId);
        await record.startRecording({ deviceId });
        console.log('Recording started successfully');
      } catch (err) {
        showError('Erreur démarrage: ' + err.message);
      }
    };

    const stopRecording = () => {
      if (record && record.isRecording()) {
        try {
          record.stopRecording();
        } catch (e) {
          console.warn('Error stopping recording:', e);
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
        console.log('Initializing visualizer...');
        if (typeof WaveSurfer === 'undefined') {
          showError('WaveSurfer non chargé');
          return;
        }
        if (typeof RecordPlugin === 'undefined') {
          showError('RecordPlugin non chargé');
          return;
        }
        console.log('WaveSurfer and RecordPlugin loaded');
        createWaveSurfer();
        const hasDevice = await ensureDevices();
        if (hasDevice) {
          console.log('Starting auto-record...');
          await startRecording();
        } else {
          showError('Aucun micro détecté');
        }
      } catch (err) {
        showError('Init error: ' + err.message);
      }
    };

    window.visualizerBridge = {
      start: startRecording,
      stop: stopRecording,
      toggle: toggleRecording,
      refreshDevices: ensureDevices,
    };

    // Attendre que WaveSurfer soit chargé
    if (typeof WaveSurfer !== 'undefined') {
      initialize();
    } else {
      window.addEventListener('load', () => {
        setTimeout(initialize, 500);
      });
    }
  </script>
</body>
</html>
"""


class Visualizer(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Micro Monitor")
        self.resize(900, 180)

        self._view = QWebEngineView()
        self._view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # Créer une page custom pour capturer les logs JS
        class DebugPage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                print(f"[JS] {message} (line {lineNumber})")
        
        page = DebugPage(self._view)
        self._view.setPage(page)
        page.featurePermissionRequested.connect(self._on_feature_permission_requested)
        self._view.loadFinished.connect(self._on_load_finished)
        
        self._view.setHtml(HTML_TEMPLATE, baseUrl=QtCore.QUrl("https://visualizer.local/"))
        self.setCentralWidget(self._view)

        self._always_on_top = True
        self._paused = False
        self._apply_window_flags()

    def _on_feature_permission_requested(self, origin: QtCore.QUrl, feature: QWebEnginePage.Feature) -> None:
        # Accorder permission pour capture audio micro
        print(f"[Permission] Feature requested: {feature}")
        # Note: setFeaturePermission est deprecated, mais nécessaire pour PySide6 < 6.8
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            if feature == QWebEnginePage.Feature.MediaAudioCapture:
                print("[Permission] Granting MediaAudioCapture permission")
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
            # Attendre un peu pour que le JS s'exécute
            QtCore.QTimer.singleShot(100, lambda: None)
        except (RuntimeError, AttributeError) as e:
            print(f"Error during close: {e}")
        super().closeEvent(event)

    def _invoke_js(self, script: str) -> None:
        self._view.page().runJavaScript(script)

    def _apply_window_flags(self) -> None:
        flags = self.windowFlags()
        if self._always_on_top:
            flags |= QtCore.Qt.WindowType.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.show()


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    visualizer = Visualizer()
    visualizer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
