"""
Test diagnostic pour identifier pourquoi la waveform ne marche pas.
"""
import sys
from PySide6 import QtCore, QtWidgets
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView


HTML_TEST = """<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8'>
    <title>Test Waveform</title>
    <style>
        body { background:#222; color:#fff; font-family:Arial; padding:20px; }
        #status { padding:10px; background:#333; border-radius:4px; margin:10px 0; }
        .ok { color:#6bff6b; }
        .error { color:#ff6b6b; }
        #mic { height:100px; background:#1a1a1a; border-radius:6px; margin:10px 0; }
    </style>
</head>
<body>
    <h2>🧪 Test Diagnostic Waveform</h2>
    <div id="status">⏳ Chargement...</div>
    <div id="mic"></div>
    <div id="logs"></div>
    
    <script src='https://unpkg.com/wavesurfer.js@7'></script>
    <script type='module'>
        const statusDiv = document.getElementById('status');
        const logsDiv = document.getElementById('logs');
        
        function log(msg, isError = false) {
            console.log(msg);
            const p = document.createElement('p');
            p.textContent = msg;
            p.className = isError ? 'error' : 'ok';
            logsDiv.appendChild(p);
        }
        
        async function test() {
            try {
                // Test 1: WaveSurfer chargé
                if (typeof WaveSurfer === 'undefined') {
                    statusDiv.innerHTML = '❌ WaveSurfer non chargé';
                    log('❌ WaveSurfer non disponible', true);
                    return;
                }
                log('✅ WaveSurfer chargé');
                
                // Test 2: Import RecordPlugin
                const RecordPlugin = await import('https://unpkg.com/wavesurfer.js@7/dist/plugins/record.esm.js');
                if (!RecordPlugin) {
                    log('❌ RecordPlugin import échoué', true);
                    return;
                }
                log('✅ RecordPlugin importé');
                
                // Test 3: Créer WaveSurfer
                const wavesurfer = WaveSurfer.create({
                    container: '#mic',
                    waveColor: 'rgb(100, 200, 255)',
                    height: 100,
                });
                log('✅ WaveSurfer instance créée');
                
                // Test 4: Enregistrer plugin
                const record = wavesurfer.registerPlugin(RecordPlugin.default.create({
                    renderRecordedAudio: false,
                    scrollingWaveform: true,
                }));
                log('✅ RecordPlugin enregistré');
                
                // Test 5: Lister devices
                const devices = await RecordPlugin.default.getAvailableAudioDevices();
                log(`✅ Devices trouvés: ${devices.length}`);
                devices.forEach((d, i) => {
                    log(`   ${i+1}. ${d.label || d.deviceId}`);
                });
                
                if (devices.length === 0) {
                    log('❌ Aucun micro détecté', true);
                    statusDiv.innerHTML = '❌ Aucun micro détecté';
                    return;
                }
                
                // Test 6: Démarrer enregistrement
                await record.startRecording({ deviceId: devices[0].deviceId });
                log('✅ Enregistrement démarré');
                statusDiv.innerHTML = '✅ TOUT FONCTIONNE - Waveform active!';
                statusDiv.className = 'ok';
                
            } catch (error) {
                log(`❌ Erreur: ${error.message}`, true);
                statusDiv.innerHTML = `❌ Erreur: ${error.message}`;
                statusDiv.className = 'error';
                console.error(error);
            }
        }
        
        // Lancer test
        window.addEventListener('load', () => {
            setTimeout(test, 1000);
        });
    </script>
</body>
</html>
"""


class TestWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Diagnostic Waveform")
        self.resize(700, 500)
        
        self._view = QWebEngineView()
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        
        # Page avec logs console
        class DebugPage(QWebEnginePage):
            def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
                level_str = ["INFO", "WARNING", "ERROR"][level]
                print(f"[JS-{level_str}] {message} (line {lineNumber})")
        
        page = DebugPage(self._view)
        self._view.setPage(page)
        page.featurePermissionRequested.connect(self._on_permission)
        
        self._view.setHtml(HTML_TEST, baseUrl=QtCore.QUrl("https://test.local/"))
        self.setCentralWidget(self._view)
    
    def _on_permission(self, origin, feature):
        print(f"[Permission] Demande: {feature}")
        if feature == QWebEnginePage.Feature.MediaAudioCapture:
            print("[Permission] ✅ Accordée: MediaAudioCapture")
            self._view.page().setFeaturePermission(
                origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser
            )
        else:
            print(f"[Permission] ❌ Refusée: {feature}")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 TEST DIAGNOSTIC WAVEFORM")
    print("=" * 60)
    print("Ce test va vérifier étape par étape:")
    print("1. Chargement WaveSurfer")
    print("2. Import RecordPlugin")
    print("3. Création instance")
    print("4. Détection microphones")
    print("5. Démarrage enregistrement")
    print("=" * 60)
    print()
    
    app = QtWidgets.QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
