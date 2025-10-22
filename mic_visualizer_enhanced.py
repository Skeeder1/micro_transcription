"""Visualizer avancé avec affichage preview temps réel via SSE.

Reçoit le texte preview depuis main_enhanced.py via Server-Sent Events
et l'affiche sous la forme d'onde pour feedback utilisateur immédiat.

Frontend: HTML/CSS/JS séparés dans visualizer_ui/
Backend: Python/Qt pour le processus de fenêtre
"""

from __future__ import annotations

import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


def get_visualizer_html_path() -> str:
    """Retourne le chemin absolu vers index.html du visualizer."""
    # Obtenir le répertoire du script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "visualizer_ui", "index.html")
    
    if not os.path.exists(html_path):
        raise FileNotFoundError(f"Fichier HTML du visualizer introuvable: {html_path}")
    
    return html_path


def inject_sse_port_into_html(html_path: str, sse_port: int) -> str:
    """Charge le HTML et injecte le port SSE dans l'attribut data-sse-port."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Remplacer le port SSE dans l'attribut data-sse-port
    html_content = html_content.replace(
        'data-sse-port="5432"',
        f'data-sse-port="{sse_port}"'
    )
    
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
        
        # Page custom pour logs
        class DebugPage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                print(f"[JS] {message} (line {lineNumber})")
        
        page = DebugPage(self._view)
        self._view.setPage(page)
        page.featurePermissionRequested.connect(self._on_feature_permission_requested)
        self._view.loadFinished.connect(self._on_load_finished)
        
        # Charger HTML depuis fichiers externes avec port SSE injecté
        try:
            html_path = get_visualizer_html_path()
            html_content = inject_sse_port_into_html(html_path, sse_port)
            
            # Créer l'URL de base pour les ressources relatives (CSS, JS)
            html_dir = os.path.dirname(html_path)
            base_url = QtCore.QUrl.fromLocalFile(html_dir + os.sep)
            
            self._view.setHtml(html_content, baseUrl=base_url)
            print(f"[Visualizer] HTML chargé depuis: {html_path}")
        except FileNotFoundError as e:
            print(f"[Visualizer] ERREUR: {e}")
            # Fallback: afficher un message d'erreur dans la fenêtre
            error_html = f"<html><body><h1>Erreur</h1><p>{e}</p></body></html>"
            self._view.setHtml(error_html)
        
        self.setCentralWidget(self._view)

        self._always_on_top = True
        self._paused = False
        self._check_window_state_timer: QtCore.QTimer | None = None
        self._apply_window_flags()

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
            # Exposer le bridge Qt vers JavaScript pour hide/show
            self._setup_qt_bridge()

    def _setup_qt_bridge(self) -> None:
        """Expose Qt methods to JavaScript for window control."""
        js_code = """
        window.qtBridge = {
            hideWindow: function() {
                console.log('[QtBridge] hideWindow called');
                window.__hideWindowRequested = true;
            },
            showWindow: function() {
                console.log('[QtBridge] showWindow called');
                window.__showWindowRequested = true;
            }
        };
        console.log('[QtBridge] Bridge initialized');
        """
        self._invoke_js(js_code)
        # Démarrer un timer pour vérifier les demandes de hide/show
        self._check_window_state_timer = QtCore.QTimer()
        self._check_window_state_timer.timeout.connect(self._check_window_state_requests)
        self._check_window_state_timer.start(100)  # Vérifier toutes les 100ms

    def _check_window_state_requests(self) -> None:
        """Check if JavaScript requested window hide/show."""
        def handle_hide(result):
            if result:
                print("[Window] Hide requested from JS")
                self.hide()
        
        def handle_show(result):
            if result:
                print("[Window] Show requested from JS")
                self.show()
        
        # Vérifier demande de masquage
        self._view.page().runJavaScript(
            "window.__hideWindowRequested || false",
            handle_hide
        )
        self._view.page().runJavaScript(
            "window.__hideWindowRequested = false; true",
            lambda _: None
        )
        
        # Vérifier demande d'affichage
        self._view.page().runJavaScript(
            "window.__showWindowRequested || false",
            handle_show
        )
        self._view.page().runJavaScript(
            "window.__showWindowRequested = false; true",
            lambda _: None
        )

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
            if self._check_window_state_timer:
                self._check_window_state_timer.stop()
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
