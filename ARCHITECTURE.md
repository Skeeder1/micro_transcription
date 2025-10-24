# Architecture Modulaire v2.0

Ce document décrit l'architecture modulaire du système de transcription audio, refactoré pour faciliter l'extensibilité et l'ajout futur de services comme AutoGen.

## Vue d'ensemble

```
transcription-audio/
├── main.py                     # Point d'entrée principal
├── core/                       # Module de transcription
├── ui/                         # Module interface utilisateur
├── api/                        # Module API REST
├── shared/                     # Utilitaires partagés
├── services/                   # Services externes (AutoGen, etc.)
├── scripts/                    # Scripts de démarrage
└── transcription_app/          # Ancien code (legacy, à supprimer)
```

## Architecture des Modules

### 1. Core Module (Transcription)

**Responsabilité** : Logique pure de transcription audio en texte

```
core/
├── __init__.py
├── config.py                   # Configuration transcription
├── engine.py                   # Bootstrap principal
├── processor.py                # Boucle de traitement audio
├── models.py                   # Gestion modèles Whisper
├── audio_capture.py            # Capture audio et presse-papier
└── audio_preprocessing.py      # Prétraitement audio
```

**Dépendances** : shared, api (pour broadcast_preview)

**Utilisation** :
```python
from core.engine import run
run()  # Lance le système de transcription
```

---

### 2. UI Module (Interface Utilisateur)

**Responsabilité** : Interface graphique de visualisation des ondes audio

```
ui/
├── __init__.py
├── __main__.py                 # Point d'entrée module
├── config.py                   # Configuration UI
├── manager.py                  # Gestion processus visualizer
├── visualizer_app.py           # Application Qt6 PySide6
└── assets/                     # Assets web (HTML/CSS/JS)
    ├── templates/
    │   └── visualizer.html
    ├── css/
    │   └── visualizer.css
    └── js/
        └── visualizer.js
```

**Dépendances** : shared, api (pour SSE)

**Utilisation** :
```bash
python -m ui.visualizer_app [port_sse]
```

---

### 3. API Module (Communication Inter-Modules)

**Responsabilité** : Serveur REST API pour la communication entre modules

```
api/
├── __init__.py
├── config.py                   # Configuration API (ports, CORS)
├── server.py                   # Serveur Flask + SSE
└── routes/
    ├── __init__.py
    ├── transcription.py        # Endpoints transcription (SSE)
    └── text_processing.py      # Endpoints AutoGen (futur)
```

**Endpoints** :
- `GET /events` : Server-Sent Events pour transcription en temps réel
- `GET /ping` : Healthcheck
- `GET /api/health` : Health check text processing (futur)
- `POST /api/reformulate/prompt` : Reformulation IA (futur AutoGen)
- `POST /api/reformulate/email` : Formatage email (futur AutoGen)

**Dépendances** : shared

**Utilisation** :
```python
from api.server import start_server, broadcast_preview
start_server(ctx)
broadcast_preview(ctx, "Message preview")
```

---

### 4. Shared Module (Utilitaires Partagés)

**Responsabilité** : Code commun utilisé par tous les modules

```
shared/
├── __init__.py
├── config.py                   # Configuration globale (agrégation)
├── context.py                  # Contexte applicatif partagé
├── hotkey.py                   # Gestion hotkeys (F9)
└── sleep.py                    # Gestion modes veille/actif
```

**Configuration** : Importe et ré-exporte toutes les configs :
- `core.config` : SAMPLE_RATE, WHISPER_MODEL, etc.
- `api.config` : SSE_PORT, SSE_HOST
- `ui.config` : VISUALIZER_START_DELAY, etc.
- Config locale : AUTO_SLEEP_SECONDS, HOTKEY_TOGGLE, etc.

**Utilisation** :
```python
from shared import config
from shared.context import AppContext
from shared.sleep import toggle_sleep_mode
```

---

### 5. Services Module (AutoGen - Futur)

**Responsabilité** : Intégration avec services externes (AutoGen, LLMs)

```
services/
├── __init__.py
├── README.md                   # Documentation intégration
└── config.py.example           # Exemple de configuration
```

**Architecture future** :
```
services/
├── config.py                   # Configuration AutoGen (API keys, etc.)
├── agents/
│   ├── prompt_agent.py         # Agent optimisation prompts
│   ├── email_agent.py          # Agent formatage emails
│   └── grammar_agent.py        # Agent correction grammaire
└── client.py                   # Client pour interagir avec agents
```

**Intégration** : Les agents seront appelés via `api/routes/text_processing.py`

---

## Flux de Communication

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                (Point d'entrée principal)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
            ┌────────────────┐
            │  core.engine   │
            │   (Bootstrap)  │
            └────────┬───────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌───────────┐  ┌──────────┐  ┌────────┐
│    UI     │  │   API    │  │ shared │
│ (Visual)  │  │ (Server) │  │(Utils) │
└─────┬─────┘  └────┬─────┘  └────────┘
      │             │
      │    SSE      │
      └─────────────┘
              │
              ▼
      ┌──────────────┐
      │   services   │
      │  (AutoGen)   │
      └──────────────┘
         (futur)
```

## Communication Inter-Modules

### 1. Core → UI (via API)
- Transcription preview : `broadcast_preview(ctx, text)`
- État système : `broadcast_state(ctx, "sleep"|"active")`

### 2. UI → Core (via shared context)
- Hotkey F9 : `toggle_sleep_mode(ctx)`
- Fermeture window : Détection par `check_visualizer_closed()`

### 3. Future: UI → Services (via API)
- Bouton "Prompt IA" → `POST /api/reformulate/prompt`
- Bouton "Email" → `POST /api/reformulate/email`

## Scripts de Démarrage

```
scripts/
├── start_transcription.bat         # Démarrage daemon (Windows)
├── start_transcription_debug.bat   # Démarrage avec logs (Windows)
├── stop_transcription.bat          # Arrêt de tous les processus
└── run_enhanced.ps1                # Démarrage PowerShell
```

**Utilisation** :
```bash
# Lancer en arrière-plan
scripts/start_transcription.bat

# Lancer en mode debug (console visible)
scripts/start_transcription_debug.bat

# Arrêter tous les processus
scripts/stop_transcription.bat
```

## Migration depuis l'Ancienne Architecture

### Ancienne Structure
```
transcription_app/
├── app.py              # Bootstrap
├── audio.py            # Audio + UI + clipboard
├── sse.py              # Serveur SSE
├── visualizer.py       # Gestion processus UI
├── static/             # Assets web
└── templates/          # Templates HTML
```

### Nouvelle Structure
```
core/           # Logique transcription pure
ui/             # Interface utilisateur séparée
api/            # API REST séparée
shared/         # Utilitaires communs
services/       # Services externes (préparé)
```

### Changements d'Imports

**Avant** :
```python
from transcription_app import config
from transcription_app.audio import make_audio_callback
from transcription_app.sse import broadcast_preview
from transcription_app.visualizer import start_visualizer
```

**Après** :
```python
from shared import config
from core.audio_capture import make_audio_callback
from api.server import broadcast_preview
from ui.manager import start_visualizer
```

## Avantages de la Nouvelle Architecture

1. **Modularité** : Chaque module a une responsabilité claire
2. **Testabilité** : Modules indépendants faciles à tester
3. **Réutilisabilité** : Le core peut être utilisé sans UI
4. **Extensibilité** : Ajout facile de nouveaux services (AutoGen)
5. **Maintenabilité** : Code organisé et facile à comprendre

## Prochaines Étapes (AutoGen)

1. **Installer AutoGen** : `pip install pyautogen`
2. **Configurer** : Copier `services/config.py.example` → `services/config.py`
3. **Implémenter agents** : Créer `services/agents/`
4. **Activer routes** : Décommenter endpoints dans `api/routes/text_processing.py`
5. **Ajouter UI** : Boutons dans le visualiseur HTML/JS

Voir [services/README.md](services/README.md) pour plus de détails.
