"""Visualiseur avec fenêtre Windows native (PySide6).

Affiche une fenêtre native qui:
- Reste toujours au premier plan
- Se masque automatiquement en mode veille
- S'affiche en mode actif
- Surveille le fichier d'état partagé
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

from shared_state import SharedState


def get_html_template() -> str:
    """Génère le template HTML intégré."""
    return """<!DOCTYPE html>
<html lang='fr'>
<head>
<meta charset='utf-8'>
<title>Visualiseur Micro</title>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<style>
  :root { color-scheme: dark; }
  body {
    background:#222;
    margin:0;
    display:flex;
    height:100vh;
    align-items:center;
    justify-content:center;
    font-family:Arial, sans-serif;
  }

  .panel {
    width:580px;
    background:#2b2b2b;
    border-radius:12px;
    padding:14px 18px 12px;
    box-shadow:0 10px 30px rgba(0,0,0,.35);
    position:relative;
    color:#ddd;
  }

  /* Waveform */
  #mic {
    height:90px;
    border-radius:6px;
    overflow:hidden;
    background:#1a1a1a;
    transition: opacity 0.3s;
  }

  /* Sleep mode */
  .panel.sleeping #mic { opacity: 0.2; }
  .panel.sleeping { background:#1a1a1a; }

  /* Toolbar */
  .toolbar {
    display:flex;
    gap:8px;
    align-items:center;
    margin-bottom:6px;
  }

  #status {
    margin:2px 0 0;
    font-size:10px;
    color:#999;
  }

  /* Preview text */
  #preview-container {
    margin-top: 10px;
    max-height: 60px;
    overflow-y: auto;
    padding: 8px;
    background: #1a1a1a;
    border-radius: 6px;
    font-size: 11px;
    line-height: 1.4;
    color: #999;
  }

  .sleeping #preview-container { opacity: 0.3; }

  #preview-text {
    margin: 0;
    word-wrap: break-word;
    white-space: pre-wrap;
  }
</style>
</head>
<body>
<div class='panel' id='panel'>
  <div class='toolbar'>
    <div style='flex:1'>
      <div style='font-weight:600; font-size:13px;'>🎤 Micro Monitor</div>
      <div id='status'>Initialisation...</div>
    </div>
  </div>
  <canvas id='mic'></canvas>
  <div id='preview-container'>
    <p id='preview-text'>En attente...</p>
  </div>
</div>

<script>
const canvas = document.getElementById('mic');
const ctx = canvas.getContext('2d');
const panel = document.getElementById('panel');
const previewText = document.getElementById('preview-text');
const statusLabel = document.getElementById('status');

// Setup canvas
canvas.width = 580;
canvas.height = 90;

// Visualizer state
let animationId = null;
let barHeights = new Array(50).fill(0);
let targetHeights = new Array(50).fill(0);

// Setup Qt WebChannel for communication with Python
let qtBridge = null;

new QWebChannel(qt.webChannelTransport, function(channel) {
  qtBridge = channel.objects.qtBridge;
  console.log('[WebChannel] Bridge connected');
});

// Animation loop
function animate() {
  // Smooth interpolation
  for (let i = 0; i < barHeights.length; i++) {
    barHeights[i] += (targetHeights[i] - barHeights[i]) * 0.15;
  }

  // Draw
  ctx.fillStyle = '#1a1a1a';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const barWidth = canvas.width / barHeights.length;

  for (let i = 0; i < barHeights.length; i++) {
    const height = barHeights[i];
    const x = i * barWidth;
    const y = (canvas.height - height) / 2;

    const gradient = ctx.createLinearGradient(x, y, x, y + height);
    gradient.addColorStop(0, '#4a9eff');
    gradient.addColorStop(0.5, '#2d7dd2');
    gradient.addColorStop(1, '#1e5a9e');

    ctx.fillStyle = gradient;
    ctx.fillRect(x + 1, y, barWidth - 2, height);
  }

  animationId = requestAnimationFrame(animate);
}

// Update preview text
function updatePreview(text) {
  if (previewText) {
    previewText.textContent = text;
  }
}

// Update status
function setStatus(text) {
  if (statusLabel) {
    statusLabel.textContent = text;
  }
}

// Handle state changes from Python
window.handleStateUpdate = function(state) {
  console.log('[JS] State update:', state);

  if (state.is_sleeping) {
    panel.classList.add('sleeping');
    updatePreview('💤 Mode veille - Appuyez sur F9');
    setStatus('Mode veille');
    if (statusLabel) {
      statusLabel.style.color = '#ff9966';
    }
  } else {
    panel.classList.remove('sleeping');
    updatePreview(state.preview_text || '🔊 Système actif');
    setStatus('Monitoring actif');
    if (statusLabel) {
      statusLabel.style.color = '#6bff6b';
    }
  }
};

// Handle preview updates
window.handlePreviewUpdate = function(text) {
  console.log('[JS] Preview update:', text);
  updatePreview(text);

  // Animate bars on preview update
  for (let i = 0; i < targetHeights.length; i++) {
    targetHeights[i] = Math.random() * 60 + 10;
  }
};

// Start animation
animate();
console.log('[Visualizer] Ready');
</script>
</body>
</html>
"""


class VisualizerWindow(QtWidgets.QMainWindow):
    """Fenêtre native du visualiseur."""

    def __init__(self) -> None:
        super().__init__()

        # Configuration fenêtre
        self.setWindowTitle("Micro Monitor")
        self.resize(600, 200)

        # Positionner en haut au centre
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        x = (screen.width() - 600) // 2
        y = 20
        self.move(x, y)

        # Configuration pour éviter la prise de focus
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        # Toujours au premier plan
        self.setWindowFlags(
            self.windowFlags() |
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )

        # Setup WebView
        self._view = QWebEngineView()
        self._view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        self._view.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        self.setCentralWidget(self._view)

        # Load HTML
        html = get_html_template()
        self._view.setHtml(html)

        # Setup Qt bridge for JS communication
        self._setup_qt_bridge()

        # Setup state watcher
        self._state = SharedState(source="visualizer_window")
        self._last_state = {"is_sleeping": False, "preview_text": ""}

        # Timer pour surveiller l'état
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self._check_state)
        self._timer.start(100)  # Check every 100ms

        print("[VisualizerWindow] Initialized")

    def _setup_qt_bridge(self) -> None:
        """Configure le bridge Qt pour communication JS <-> Python."""

        class Bridge(QtCore.QObject):
            """Bridge pour communication bidirectionnelle."""

            def __init__(self, parent_window):
                super().__init__()
                self.parent_window = parent_window

        self._bridge = Bridge(self)
        self._channel = QWebChannel()
        self._channel.registerObject("qtBridge", self._bridge)
        self._view.page().setWebChannel(self._channel)

    def _check_state(self) -> None:
        """Vérifie l'état et met à jour la fenêtre."""
        try:
            state = self._state.get_state()

            # Check if state changed
            if state["is_sleeping"] != self._last_state["is_sleeping"]:
                if state["is_sleeping"]:
                    print("[VisualizerWindow] Sleep mode - hiding window")
                    self.hide()
                else:
                    print("[VisualizerWindow] Active mode - showing window")
                    self.show()

                # Update JS
                self._invoke_js(f"window.handleStateUpdate({state})")

            # Check if preview changed
            if state.get("preview_text") != self._last_state.get("preview_text"):
                preview = state.get("preview_text", "")
                if preview:
                    self._invoke_js(f"window.handlePreviewUpdate('{preview}')")

            self._last_state = state.copy()

        except Exception as e:
            print(f"[VisualizerWindow] Error checking state: {e}")

    def _invoke_js(self, script: str) -> None:
        """Exécute du JavaScript dans la page."""
        self._view.page().runJavaScript(script)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Gère les événements clavier."""
        if event.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Nettoyage à la fermeture."""
        self._timer.stop()
        super().closeEvent(event)


def main() -> None:
    """Point d'entrée."""
    app = QtWidgets.QApplication(sys.argv)
    window = VisualizerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
