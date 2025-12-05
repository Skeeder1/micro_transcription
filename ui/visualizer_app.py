"""Visualizer avancé avec affichage preview temps réel via SSE.

Reçoit le texte preview depuis le core via Server-Sent Events
et l'affiche sous la forme d'onde pour feedback utilisateur immédiat.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


def get_resource_content(resource_path: str) -> str:
    """Load CSS or JS file content from the assets directory."""
    base_dir = Path(__file__).parent / "assets"
    file_path = base_dir / resource_path.lstrip('/')

    if not file_path.exists():
        raise FileNotFoundError(f"Resource not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def get_html_template(sse_port: int) -> str:
    """Load HTML template from file and inject SSE port, CSS, and JS."""
    base_dir = Path(__file__).parent / "assets"
    template_path = base_dir / "templates" / "visualizer.html"

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Load template
    with open(template_path, 'r', encoding='utf-8') as f:
        html_content = f.read()

    # Load CSS and JS content
    css_content = get_resource_content("css/visualizer.css")
    js_content = get_resource_content("js/visualizer.js")

    # Replace qrc:// links with inline content
    html_content = html_content.replace(
        '<link rel="stylesheet" href="qrc:///static/css/visualizer.css">',
        f'<style>\n{css_content}\n</style>'
    )

    html_content = html_content.replace(
        '<script src="qrc:///static/js/visualizer.js"></script>',
        f'<script>\n{js_content}\n</script>'
    )

    # Replace the SSE_PORT placeholder
    html_content = html_content.replace('{{SSE_PORT}}', str(sse_port))

    return html_content


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
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PluginsEnabled, True)
        # Important pour le microphone
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScreenCaptureEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)

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
        print(f"[Permission] Feature requested: {feature} from {origin}")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            # Autoriser tous les types de capture audio/vidéo
            allowed_features = [
                QWebEnginePage.Feature.MediaAudioCapture,
                QWebEnginePage.Feature.MediaVideoCapture,
                QWebEnginePage.Feature.MediaAudioVideoCapture,
            ]
            if feature in allowed_features:
                print(f"[Permission] Granting {feature}")
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
