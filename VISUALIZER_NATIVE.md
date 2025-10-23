# Visualiseur avec Fenêtre Native Windows

## 🎯 Vue d'ensemble

Le système de visualisation utilise maintenant une **fenêtre Windows native** (PySide6) au lieu d'un navigateur web. Cette fenêtre reste **toujours au premier plan** et se masque automatiquement avec la touche **F9**.

## 🔧 Architecture

### Fichiers principaux

```
visualizer_window.py     ← Fenêtre native PySide6 avec QWebEngineView
shared_state.py          ← État partagé entre transcription et visualiseur
start.bat                ← Script de démarrage (lance la fenêtre native)
```

### Flux de communication

```
[main_enhanced.py] ──────► [shared_state.py] ◄────── [visualizer_window.py]
   (Transcription)              (État JSON)              (Fenêtre native)
         │                           │                          │
         │ F9 pressé                 │                          │
         ├──► set_sleep_state(True)  │                          │
         │                           ├──► {"is_sleeping": true} │
         │                           │                          │
         │                           │ ◄──── poll toutes 100ms ─┤
         │                           │                          │
         │                           │ ──► window.hide() ───────┤
```

## ⌨️ Hotkey F9

### Comportement

- **F9** : Bascule entre mode actif et mode veille
- **Mode actif** : Fenêtre visible, système écoute
- **Mode veille** : Fenêtre masquée, système en pause

### Implémentation

```python
# transcription_app/hotkey.py
class HotkeyManager:
    def _handle_press(self, key):
        if key == pynput_keyboard.Key.f9:
            self._on_toggle()  # Bascule l'état
```

```python
# visualizer_window.py
def _check_state(self):
    state = self._state.get_state()
    if state["is_sleeping"]:
        self.hide()  # Masque la fenêtre
    else:
        self.show()  # Affiche la fenêtre
```

## 🪟 Fenêtre Native (PySide6)

### Caractéristiques

- **Toujours au premier plan** : `WindowStaysOnTopHint`
- **Ne vole pas le focus** : `WindowDoesNotAcceptFocus`
- **WebEngine intégré** : Affiche l'interface HTML/CSS/JS
- **Position fixe** : Haut-centre de l'écran

### Avantages vs navigateur web

✅ Reste au premier plan automatiquement  
✅ Masquage instantané avec F9  
✅ Pas de barre d'adresse/onglets  
✅ Intégration système Windows native  
✅ Pas de console Python visible (pythonw.exe)  

### Code clé

```python
class VisualizerWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # Configuration pour rester au premier plan
        self.setWindowFlags(
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.WindowDoesNotAcceptFocus
        )
        
        # WebEngine pour afficher l'interface
        self._view = QWebEngineView()
        self._view.setHtml(get_html_template())
        self.setCentralWidget(self._view)
```

## 🚀 Démarrage

### Méthode automatique (recommandée)

```batch
start.bat
```

Ce script :
1. ✅ Lance `visualizer_window.py` en arrière-plan (fenêtre native)
2. ✅ Lance `main_enhanced.py` au premier plan (transcription)
3. ✅ Nettoie tout à l'arrêt

### Méthode manuelle

```powershell
# Terminal 1 : Visualiseur (fenêtre native)
.\.venv\Scripts\pythonw.exe visualizer_window.py

# Terminal 2 : Transcription
.\.venv\Scripts\python.exe main_enhanced.py
```

> **Note** : Utiliser `pythonw.exe` pour le visualiseur évite d'afficher une console.

## 📊 État partagé (shared_state.py)

### Format JSON

```json
{
  "is_sleeping": false,
  "last_update": 1729705123.456,
  "preview_text": "Texte en cours...",
  "source": "transcription"
}
```

### API

```python
from shared_state import SharedState

state = SharedState(source="visualizer")

# Lecture
is_sleeping = state.get_sleep_state()
preview = state.get_preview_text()
full_state = state.get_state()

# Écriture
state.set_sleep_state(True)
state.set_preview_text("Nouveau texte")
```

### Synchronisation

- **Polling** : Le visualiseur vérifie l'état toutes les **100ms**
- **Atomicité** : Écriture via fichier temporaire + rename
- **Source tracking** : Identifie qui a modifié l'état

## 🧪 Tests

### Test rapide de la fenêtre

```powershell
.\.venv\Scripts\python.exe test_native_window.py
```

Affiche la fenêtre pendant 5 secondes puis la ferme.

### Test de l'état partagé

```powershell
.\.venv\Scripts\python.exe -c "from shared_state import SharedState; s = SharedState('test'); print(s.get_state())"
```

### Test du hotkey F9

```powershell
.\.venv\Scripts\python.exe main_enhanced.py
```

Puis appuyez sur **F9** pour basculer l'état.

## 🔧 Dépendances

### Visualiseur (fenêtre native)

```
PySide6>=6.6.0
PySide6-WebEngine>=6.6.0
```

### Installation

```powershell
.\.venv\Scripts\python.exe -m pip install PySide6 PySide6-WebEngine
```

## 📝 Notes techniques

### Pourquoi PySide6 ?

- **Qt WebEngine** : Moteur Chromium intégré pour l'interface web
- **Native** : Véritable fenêtre Windows (pas d'émulation)
- **Performance** : Rendu GPU, animations fluides
- **Contrôle total** : Gestion fine du comportement de la fenêtre

### Communication JS ↔ Python

```javascript
// JavaScript (dans la fenêtre)
window.handleStateUpdate = function(state) {
  if (state.is_sleeping) {
    panel.classList.add('sleeping');
  }
}
```

```python
# Python (depuis visualizer_window.py)
self._view.page().runJavaScript(
    f"window.handleStateUpdate({state})"
)
```

### Masquage vs fermeture

- **Masquage** (`hide()`) : La fenêtre reste en mémoire
- **Fermeture** (`close()`) : La fenêtre est détruite

Le système utilise le masquage pour des transitions rapides.

## 🎨 Interface HTML/CSS/JS

L'interface est **intégrée** dans `visualizer_window.py` :

```python
def get_html_template() -> str:
    return """<!DOCTYPE html>
    <html>
      <!-- Interface complète ici -->
    </html>
    """
```

Avantages :
- ✅ Pas de fichiers externes à gérer
- ✅ Déploiement simplifié (un seul fichier .py)
- ✅ Pas de serveur HTTP nécessaire

## 🐛 Dépannage

### La fenêtre ne s'affiche pas

```powershell
# Vérifier les dépendances
.\.venv\Scripts\python.exe -c "import PySide6; print('OK')"
```

### La fenêtre ne reste pas au premier plan

Vérifier dans `visualizer_window.py` :
```python
self.setWindowFlags(
    QtCore.Qt.WindowType.WindowStaysOnTopHint  # ← Important
)
```

### F9 ne masque pas la fenêtre

Vérifier l'état partagé :
```powershell
Get-Content .app_state.json
```

### La fenêtre laisse une console visible

Utiliser `pythonw.exe` au lieu de `python.exe` :
```batch
start "" .venv\Scripts\pythonw.exe visualizer_window.py
```

## 🎯 Prochaines améliorations possibles

- [ ] Animations de transition (fade in/out)
- [ ] Taille de fenêtre configurable
- [ ] Position configurable (coins de l'écran)
- [ ] Mode "always on top" optionnel
- [ ] Thèmes (clair/sombre)
- [ ] Raccourcis clavier additionnels

## 📚 Références

- [PySide6 Documentation](https://doc.qt.io/qtforpython-6/)
- [Qt WebEngine](https://doc.qt.io/qt-6/qtwebengine-index.html)
- [pynput Documentation](https://pynput.readthedocs.io/)

---

**Résumé** : Le visualiseur utilise maintenant une fenêtre Windows native (PySide6) qui reste toujours au premier plan et se masque automatiquement avec F9. Communication via `shared_state.py` (fichier JSON). Démarrage avec `start.bat`. ✅
