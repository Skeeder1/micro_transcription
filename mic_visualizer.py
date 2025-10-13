"""Microphone visualizer using WaveSurfer.js embedded in a Qt WebEngine window.

Install dependencies:
    pip install --upgrade pip
    pip install PySide6 sounddevice numpy
"""

from __future__ import annotations

import sys

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PySide6.QtWebEngineWidgets import QWebEngineView

HTML_TEMPLATE = r"""<!doctype html>
<html lang=\"fr\">
<head>
<meta charset=\"utf-8\" />
<title>Visualiseur micro</title>
<style>
  body{background:#222;margin:0;display:flex;height:100vh;align-items:center;justify-content:center;font-family:sans-serif;color:#eee}
  .panel{width:900px;height:160px;background:#2b2b2b;border-radius:16px;padding:20px 28px;box-shadow:0 10px 30px rgba(0,0,0,.35);position:relative;box-sizing:border-box}
  #mic{height:96px;border-radius:8px;border:1px solid #3d3d3d;background:#1d1d1d;margin-top:16px}
  .panel::after{content:\"\";display:block;height:0;border-top:2px dotted #555;position:absolute;left:28px;right:28px;top:104px}
  .toolbar{display:flex;align-items:center;gap:12px;font-size:13px}
  button{background:#3a3a3a;color:#ddd;border:0;padding:6px 12px;border-radius:6px;cursor:pointer;min-width:72px}
  button:disabled{opacity:0.5;cursor:default}
  select{background:#3a3a3a;color:#ddd;border:0;border-radius:6px;padding:6px 10px}
  label{display:flex;align-items:center;gap:6px}
  #progress{margin-left:auto;font-variant-numeric:tabular-nums}
  #recordings{margin-top:12px;display:flex;flex-direction:column;gap:8px}
  #recordings button{min-width:64px}
  #recordings a{color:#9fc9ff;text-decoration:none;font-size:12px;margin-left:8px}
</style>
</head>
<body>
  <div class=\"panel\">
    <div class=\"toolbar\">
      <button id=\"record\">Record</button>
      <button id=\"pause\" style=\"display:none;\">Pause</button>
      <select id=\"mic-select\">
        <option value=\"\" hidden>Micro par défaut</option>
      </select>
      <label><input type=\"checkbox\" id=\"scrollingWaveform\" />Scrolling</label>
      <label><input type=\"checkbox\" id=\"continuousWaveform\" checked />Continu</label>
      <span id=\"progress\">00:00</span>
    </div>
    <div id=\"mic\"></div>
    <div id=\"recordings\"></div>
  </div>

  <script type=\"module\">
    import WaveSurfer from 'https://unpkg.com/wavesurfer.js@7/dist/wavesurfer.esm.js';
    import RecordPlugin from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/record.esm.js';

    const micContainer = document.querySelector('#mic');
    const recordingsContainer = document.querySelector('#recordings');
    const progress = document.querySelector('#progress');
    const pauseButton = document.querySelector('#pause');
    const recButton = document.querySelector('#record');
    const micSelect = document.querySelector('#mic-select');
    const scrollingCheckbox = document.querySelector('#scrollingWaveform');
    const continuousCheckbox = document.querySelector('#continuousWaveform');

    let wavesurfer;
    let record;
    let scrollingWaveform = scrollingCheckbox.checked;
    let continuousWaveform = continuousCheckbox.checked;

    const formatTime = (timeMs) => {
      const minutes = Math.floor((timeMs % 3600000) / 60000);
      const seconds = Math.floor((timeMs % 60000) / 1000);
      return [minutes, seconds].map((v) => (v < 10 ? '0' + v : String(v))).join(':');
    };

    const updateProgress = (time) => {
      progress.textContent = formatTime(time);
    };

    const resetUi = () => {
      pauseButton.style.display = 'none';
      pauseButton.textContent = 'Pause';
      recButton.textContent = 'Record';
      recButton.disabled = false;
      updateProgress(0);
    };

    const createWaveSurfer = () => {
      if (wavesurfer) {
        wavesurfer.destroy();
      }

      wavesurfer = WaveSurfer.create({
        container: micContainer,
        waveColor: 'rgb(200, 0, 200)',
        progressColor: 'rgb(100, 0, 100)',
        interact: false,
      });

      record = wavesurfer.registerPlugin(
        RecordPlugin.create({
          renderRecordedAudio: false,
          scrollingWaveform,
          continuousWaveform,
          continuousWaveformDuration: 30,
        }),
      );

      record.on('record-end', (blob) => {
        resetUi();
        const entry = document.createElement('div');
        entry.style.display = 'flex';
        entry.style.alignItems = 'center';
        entry.style.gap = '8px';

        const waveHolder = document.createElement('div');
        waveHolder.style.width = '280px';
        waveHolder.style.height = '48px';
        waveHolder.style.flexShrink = '0';
        entry.appendChild(waveHolder);

        const recordedUrl = URL.createObjectURL(blob);

        const preview = WaveSurfer.create({
          container: waveHolder,
          waveColor: 'rgb(200, 100, 0)',
          progressColor: 'rgb(100, 50, 0)',
          height: 48,
          url: recordedUrl,
        });

        const playButton = document.createElement('button');
        playButton.textContent = 'Play';
        playButton.onclick = () => preview.playPause();
        preview.on('pause', () => (playButton.textContent = 'Play'));
        preview.on('play', () => (playButton.textContent = 'Pause'));
        entry.appendChild(playButton);

        const link = document.createElement('a');
        const extension = blob.type.split(';')[0].split('/')[1] || 'webm';
        Object.assign(link, {
          href: recordedUrl,
          download: 'recording.' + extension,
          textContent: 'Download',
        });
        entry.appendChild(link);

        recordingsContainer.appendChild(entry);
      });

      record.on('record-progress', (time) => {
        updateProgress(time);
      });

      resetUi();
    };

    pauseButton.onclick = () => {
      if (!record) {
        return;
      }
      if (record.isPaused()) {
        record.resumeRecording();
        pauseButton.textContent = 'Pause';
      } else {
        record.pauseRecording();
        pauseButton.textContent = 'Resume';
      }
    };

    micSelect.onchange = () => {
      // no-op: device applied when recording starts
    };

    recButton.onclick = () => {
      if (!record) {
        return;
      }

      if (record.isRecording() || record.isPaused()) {
        record.stopRecording();
        resetUi();
        return;
      }

      recButton.disabled = true;
      const deviceId = micSelect.value || undefined;
      const options = deviceId ? { deviceId } : undefined;
      record
        .startRecording(options)
        .then(() => {
          recButton.textContent = 'Stop';
          recButton.disabled = false;
          pauseButton.style.display = 'inline';
          pauseButton.textContent = 'Pause';
          updateProgress(0);
        })
        .catch(() => {
          resetUi();
        });
    };

    scrollingCheckbox.onchange = (event) => {
      const next = event.target.checked;
      scrollingWaveform = next;
      if (next && continuousWaveform) {
        continuousWaveform = false;
        continuousCheckbox.checked = false;
      }
      createWaveSurfer();
    };

    continuousCheckbox.onchange = (event) => {
      const next = event.target.checked;
      continuousWaveform = next;
      if (next && scrollingWaveform) {
        scrollingWaveform = false;
        scrollingCheckbox.checked = false;
      }
      createWaveSurfer();
    };

    RecordPlugin.getAvailableAudioDevices().then((devices) => {
      devices.forEach((device) => {
        const option = document.createElement('option');
        option.value = device.deviceId;
        option.text = device.label || device.deviceId;
        micSelect.appendChild(option);
      });
      if (!micSelect.value && devices.length > 0) {
        micSelect.value = devices[0].deviceId;
      }
    });

    createWaveSurfer();

    window.visualizerControl = {
      start: () => {
        if (!record) {
          return;
        }
        if (record.isRecording()) {
          return;
        }
        recButton.click();
      },
      stop: () => {
        if (!record) {
          return;
        }
        if (record.isRecording() || record.isPaused()) {
          record.stopRecording();
          resetUi();
        }
      },
      toggle: () => {
        if (!record) {
          return;
        }
        if (record.isRecording() || record.isPaused()) {
          recButton.click();
        } else {
          recButton.click();
        }
      },
      togglePause: () => {
        if (!record) {
          return;
        }
        if (record.isPaused()) {
          record.resumeRecording();
          pauseButton.textContent = 'Pause';
        } else if (record.isRecording()) {
          record.pauseRecording();
          pauseButton.textContent = 'Resume';
        } else {
          recButton.click();
        }
      },
    };
  </script>
</body>
</html>
"""


class Visualizer(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Micro Visualizer")
        self.resize(900, 200)

        self._view = QWebEngineView()
        self._view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.NoContextMenu)
        settings = self._view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        self.setCentralWidget(self._view)

        page = self._view.page()
        page.featurePermissionRequested.connect(self._on_feature_permission_requested)
        self._view.loadFinished.connect(self._on_load_finished)
        self._view.setHtml(HTML_TEMPLATE, baseUrl=QtCore.QUrl("https://visualizer.local/"))

        self._always_on_top = True
        self._apply_window_flags()

    def _on_feature_permission_requested(
        self, security_origin: QtCore.QUrl, feature: QWebEnginePage.Feature
    ) -> None:
        if feature == QWebEnginePage.Feature.MediaAudioCapture:
            self._view.page().setFeaturePermission(
                security_origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            )
        else:
            self._view.page().setFeaturePermission(
                security_origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionDeniedByUser,
            )

    def _on_load_finished(self, ok: bool) -> None:
        if ok:
            self._invoke_js("window.visualizerControl && window.visualizerControl.start();")

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key = event.key()
        if key == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif key == QtCore.Qt.Key.Key_Space:
            self._invoke_js("window.visualizerControl && window.visualizerControl.togglePause();")
        elif key == QtCore.Qt.Key.Key_T:
            self._always_on_top = not self._always_on_top
            self._apply_window_flags()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._invoke_js("window.visualizerControl && window.visualizerControl.stop();")
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
