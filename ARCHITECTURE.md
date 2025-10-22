# Architecture du projet - Transcription Audio

## 📁 Structure des dossiers

```
transcription-audio/
├── visualizer_ui/              # 🎨 FRONTEND - Interface utilisateur
│   ├── index.html             # Structure HTML du visualizer
│   ├── style.css              # Styles de l'interface
│   └── app.js                 # Logique JavaScript (SSE, audio, UI)
│
├── transcription_app/          # 🔧 BACKEND - Logique métier Python
│   ├── __init__.py
│   ├── app.py                 # Point d'entrée principal
│   ├── audio.py               # Capture audio et détection activité
│   ├── config.py              # Configuration globale
│   ├── context.py             # État partagé de l'application
│   ├── hotkey.py              # Gestion hotkey F9
│   ├── main_loop.py           # Boucle principale audio
│   ├── models.py              # Gestion modèles Whisper (IA)
│   ├── sleep.py               # Gestion veille/veille profonde
│   ├── sse.py                 # Serveur Server-Sent Events
│   └── visualizer.py          # Gestion processus visualizer Qt
│
├── mic_visualizer_enhanced.py  # 🪟 Pont Python/Qt → Frontend
├── main_enhanced.py            # Script de lancement
└── README.md                   # Documentation
```

## 🔄 Séparation Frontend / Backend

### Frontend (Interface Graphique) 🎨
**Dossier**: `visualizer_ui/`
**Technologies**: HTML5, CSS3, JavaScript (ES6+), WaveSurfer.js
**Responsabilités**:
- Afficher la forme d'onde du microphone
- Afficher le texte prévisualisation en temps réel
- Gérer l'état visuel (veille/actif)
- Recevoir les messages SSE du backend
- Interface utilisateur responsive

**Fichiers**:
- `index.html`: Structure DOM et imports
- `style.css`: Styles visuels (dark theme, animations)
- `app.js`: Logique application (SSE, WaveSurfer, gestion état)

### Backend (Traitement) 🔧
**Dossier**: `transcription_app/`
**Technologies**: Python 3.11+, faster-whisper, Flask, sounddevice
**Responsabilités**:
- Capture audio du microphone
- Transcription vocale (modèles Whisper IA)
- Gestion de l'état (veille, veille profonde)
- Serveur SSE pour communication frontend
- Gestion mémoire (chargement/déchargement modèles)

**Modules clés**:
- `models.py`: Chargement/déchargement modèles Whisper
- `audio.py`: Capture audio et détection d'activité vocale
- `sleep.py`: États veille (rapide et profonde)
- `sse.py`: Communication temps réel vers frontend

### Pont Python/Qt 🪟
**Fichier**: `mic_visualizer_enhanced.py`
**Technologies**: PySide6 (Qt for Python), QtWebEngine
**Responsabilités**:
- Créer la fenêtre native du système
- Charger le frontend HTML/CSS/JS
- Bridge entre Python et JavaScript
- Gestion visibilité fenêtre (hide/show)

## 🔌 Communication Frontend ↔️ Backend

### Server-Sent Events (SSE)
```
Backend (Python)                Frontend (JavaScript)
    │                                  │
    ├─ broadcast_preview("texte")     │
    │  ────────────────────────────>  │
    │                                  ├─ updatePreview()
    │                                  │
    ├─ broadcast_state("sleep")       │
    │  ────────────────────────────>  │
    │                                  ├─ handleStateChange()
    │                                  └─ qtBridge.hideWindow()
    │                                       │
    │  <────────────────────────────────── │
    └─ self.hide() (Qt)
```

### Messages SSE
- **Texte preview**: Chaîne simple → affiché dans `#preview-text`
- **Commande d'état**: `__STATE__sleep` ou `__STATE__active`

### Bridge Qt ↔️ JavaScript
```javascript
// JavaScript appelle Qt
window.qtBridge.hideWindow();  // Masque la fenêtre
window.qtBridge.showWindow();  // Affiche la fenêtre

// Qt vérifie périodiquement (timer 100ms)
// et exécute self.hide() ou self.show()
```

## 🎯 Flux de données

### 1. Capture audio
```
Microphone
  └─> sounddevice.InputStream (audio.py)
       └─> audio_queue (context.py)
            └─> main_loop.py
                 ├─> Preview (3s buffer)
                 │    └─> transcribe_preview() → SSE → Frontend
                 └─> Production (silence flush)
                      └─> transcribe_production() → Presse-papiers
```

### 2. Gestion veille
```
Actif (F9)
  └─> enter_sleep_mode() → broadcast_state("sleep")
       └─> Frontend masque fenêtre
            └─> 10 minutes → enter_deep_sleep_mode()
                 ├─> unload_models() (libère RAM)
                 └─> stop_visualizer() (ferme fenêtre)

Réactivation (F9)
  └─> exit_sleep_mode()
       ├─ Si veille rapide: broadcast_state("active") → instantané
       └─ Si veille profonde:
            ├─> init_models() (recharge IA ~3-5s)
            ├─> start_visualizer() (relance fenêtre)
            └─> broadcast_state("active")
```

## 🚀 Avantages de cette architecture

### Séparation des responsabilités
✅ **Frontend**: Uniquement l'UI et les interactions utilisateur
✅ **Backend**: Logique métier, IA, traitement audio
✅ **Pont Qt**: Interface système natif

### Maintenabilité
✅ Fichiers propres par langage (HTML, CSS, JS, Python)
✅ Modification CSS/JS sans toucher Python
✅ Tests frontend/backend indépendants

### Performance
✅ Chargement HTML depuis fichiers (pas de string Python géant)
✅ CSS/JS minifiables et cachables
✅ SSE asynchrone pour communication temps réel

### Évolutivité
✅ Facile d'ajouter de nouveaux modules backend
✅ Frontend peut évoluer vers React/Vue si besoin
✅ API SSE peut servir d'autres clients

## 📝 Conventions de code

### Python (Backend)
- PEP 8 style guide
- Type hints obligatoires
- Docstrings pour fonctions publiques
- Gestion erreurs avec try/except

### JavaScript (Frontend)
- ES6+ modules
- Const/let (pas de var)
- Async/await pour asynchrone
- Console.log pour debug

### HTML/CSS
- HTML5 sémantique
- CSS3 moderne (flexbox, animations)
- Mobile-first (responsive)
- Dark theme par défaut

## 🔧 Développement

### Modifier l'interface
```bash
# Éditer visualizer_ui/style.css pour les styles
# Éditer visualizer_ui/app.js pour la logique
# Éditer visualizer_ui/index.html pour la structure
# Recharger l'application Python pour voir les changements
```

### Modifier le backend
```bash
# Éditer transcription_app/*.py
# Relancer main_enhanced.py
```

### Debug
```bash
# Backend: logs dans console Python
# Frontend: logs dans console JavaScript (F12 dans navigateur)
```

## 📦 Dépendances

### Python
- PySide6 (Qt)
- faster-whisper (IA transcription)
- Flask (serveur SSE)
- sounddevice (audio)
- numpy, pyperclip, pynput

### JavaScript (CDN)
- WaveSurfer.js 7.x
- RecordPlugin (module ES6)

---

**Architecture créée le**: 22 octobre 2025
**Objectif**: Séparation claire frontend/backend, maintenabilité, performance
