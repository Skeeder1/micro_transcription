# Architecture du Système - Modules Indépendants

## 🏗️ Vue d'Ensemble

Le système est composé de **2 modules complètement indépendants** qui communiquent via un **fichier d'état partagé**.

```
┌─────────────────────────────────────┐
│   Module 1: Transcription Vocale   │
│  (transcription_app/)               │
│  - Capture audio                    │
│  - Transcription Whisper            │
│  - Hotkey F9                        │
│  - Écrit dans shared_state          │
└─────────────┬───────────────────────┘
              │
              │ Fichier d'état partagé
              │ (.app_state.json)
              │
┌─────────────▼───────────────────────┐
│   Module 2: Visualiseur Audio      │
│  (visualizer/)                      │
│  - Serveur web Flask                │
│  - Interface ondes                  │
│  - Lit shared_state                 │
│  - Met à jour UI                    │
└─────────────────────────────────────┘
```

## 📦 Module 1: Transcription Vocale

### Responsabilités
- ✅ Capture audio en temps réel
- ✅ Transcription avec Whisper
- ✅ Gestion du mode veille (F9)
- ✅ Collage au curseur
- ✅ **Écrit** l'état dans le fichier partagé

### Fichiers Clés
```
transcription_app/
├── app.py              # Point d'entrée
├── state_manager.py    # 🆕 Gestion état partagé
├── sleep.py            # Gestion veille/actif
├── main_loop.py        # Boucle audio
└── ...
```

### Indépendance
- ✅ **Fonctionne seul** sans visualiseur
- ✅ Pas de dépendance au visualiseur
- ✅ Pas d'appels réseau
- ✅ Communication uniquement via fichier

## 📊 Module 2: Visualiseur Audio

### Responsabilités
- ✅ Interface web (ondes audio)
- ✅ **Lit** l'état du fichier partagé
- ✅ Met à jour l'UI en temps réel
- ✅ API REST (optionnelle)

### Fichiers Clés
```
visualizer/
├── server.py           # Launcher
├── app.py              # Flask app
├── state_watcher.py    # 🆕 Surveillance état
├── templates/          # Interface web
└── static/             # CSS/JS
```

### Indépendance
- ✅ **Fonctionne seul** sans transcription
- ✅ Peut être lancé sur une autre machine
- ✅ Accès via navigateur web
- ✅ Communication uniquement via fichier

## 🔄 État Partagé (Fichier JSON)

### Format
```json
{
  "is_sleeping": false,
  "last_update": 1234567890.123,
  "preview_text": "Transcription en cours...",
  "source": "transcription"
}
```

### Flux de Données

#### 1. Transcription → Visualiseur
```
Utilisateur parle
     ↓
transcription_app transcrit
     ↓
Écrit dans .app_state.json
     ↓
visualizer/state_watcher détecte
     ↓
Broadcast SSE vers navigateur
     ↓
UI se met à jour
```

#### 2. F9 Pressed
```
F9 dans transcription_app
     ↓
toggle_sleep_mode()
     ↓
Écrit dans .app_state.json
     ↓
visualizer/state_watcher détecte
     ↓
UI change d'apparence (veille/actif)
```

## 🔌 API REST (Optionnelle)

Le visualiseur expose une API REST pour contrôle externe:

```
GET  /api/status      # Lire l'état
POST /api/preview     # Définir texte (externe)
POST /api/state       # Définir état (externe)
POST /api/clear       # Effacer preview
```

**Note**: L'API est optionnelle. Les deux modules communiquent principalement via le fichier d'état.

## 🚀 Démarrage

### Option 1: Les Deux Ensemble
```bash
# Terminal 1: Lancer le visualiseur
python run_visualizer.py

# Terminal 2: Lancer la transcription
python main_enhanced.py
```
- Lance le visualiseur dans un terminal
- Lance la transcription dans un autre terminal
- Synchronisés via fichier

### Option 2: Transcription Seule
```bash
python main_enhanced.py
```
- Fonctionne sans visualiseur
- F9 fonctionne normalement
- Pas d'affichage ondes

### Option 3: Visualiseur Seul
```bash
python run_visualizer.py
```
- Peut être lancé avant/après
- S'affiche si transcription active
- Sinon reste vide

## 🎯 Avantages de cette Architecture

### 1. Découplage Total
- ❌ Pas de dépendance directe
- ✅ Modification d'un module n'affecte pas l'autre
- ✅ Testable indépendamment

### 2. Scalabilité
- ✅ Visualiseur peut tourner sur autre machine
- ✅ Plusieurs visualiseurs peuvent lire le même état
- ✅ Facile d'ajouter d'autres modules

### 3. Robustesse
- ✅ Si visualiseur crash → transcription continue
- ✅ Si transcription crash → visualiseur reste ouvert
- ✅ Pas de blocage réseau

### 4. Simplicité
- ✅ Fichier JSON simple
- ✅ Pas besoin de serveur complexe
- ✅ Debugging facile (lire le fichier)

## 📁 Fichier d'État

### Localisation
```
C:\GitHub\transcription-audio\.app_state.json
```

### Lecture Manuelle
```bash
type .app_state.json
```

### Effacement
Le fichier est recréé automatiquement au démarrage.

## 🔒 Thread-Safety

### Écriture (transcription_app)
```python
from shared_state import SharedState

state = SharedState(source="transcription")
state.set_sleep_state(True)  # Atomique
state.set_preview_text("...")  # Atomique
```

### Lecture (visualizer)
```python
watcher = StateWatcher(
    on_state_change=callback,
    on_preview_change=callback
)
watcher.start()  # Poll toutes les 100ms
```

## 🧪 Tests

### Test Transcription Seule
```bash
python main_enhanced.py
# → Devrait fonctionner sans visualiseur
# → F9 devrait basculer veille/actif
```

### Test Visualiseur Seul
```bash
python run_visualizer.py
# Ouvrir http://127.0.0.1:5500
# → Interface devrait être visible
# → Vide si transcription pas lancée
```

### Test Synchronisation
```bash
# Terminal 1
python run_visualizer.py

# Terminal 2
python main_enhanced.py

# → Les deux se synchronisent via .app_state.json
# → F9 dans transcription change visualiseur
```

## 📊 Performances

### Overhead
- **Fichier**: < 1 KB
- **Polling**: 100ms (visualiseur)
- **Latence**: ~100-200ms (acceptable)

### Optimisation Possible
- Utiliser inotify/watchdog pour events
- Réduire polling à 50ms
- Utiliser socket local au lieu de fichier

## 🔮 Évolutions Futures

### Possibilités
1. **Multi-instances**: Plusieurs visualiseurs
2. **Logging**: Historique des états
3. **Replay**: Rejouer les transcriptions
4. **Remote**: Visualiseur sur autre machine
5. **Mobile**: App mobile qui lit l'état

## 📝 Notes Importantes

1. **Le fichier .app_state.json est ignoré par Git** (ajoutez-le à .gitignore)
2. **Les deux modules sont thread-safe** grâce à la gestion atomique des fichiers
3. **Pas besoin de socket/réseau** pour la communication locale
4. **Le visualiseur détecte automatiquement** les changements d'état

## ✅ Résumé

| Aspect | Transcription | Visualiseur |
|--------|---------------|-------------|
| **Indépendance** | ✅ Fonctionne seul | ✅ Fonctionne seul |
| **Communication** | Écrit fichier | Lit fichier |
| **Dépendances** | Aucune sur visualiseur | Aucune sur transcription |
| **F9** | Gère le hotkey | Réagit aux changements |
| **Interface** | Console | Web |
| **Lancement** | Optionnel | Optionnel |

**Conclusion**: Les deux modules sont **complètement découplés** et communiquent via un fichier d'état partagé simple et efficace.
