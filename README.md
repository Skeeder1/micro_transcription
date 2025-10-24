# Système de Transcription Audio Avancé v2.0

Système de dictée vocale avec interface graphique, transcription en temps réel via Whisper, et architecture modulaire préparée pour AutoGen.

## Architecture Modulaire

```
transcription-audio/
├── main.py                     # Point d'entrée principal
│
├── core/                       # Module transcription (logique pure)
│   ├── engine.py              # Bootstrap de l'application
│   ├── processor.py           # Boucle de traitement audio
│   ├── models.py              # Gestion modèles Whisper
│   ├── audio_capture.py       # Capture audio et presse-papier
│   ├── audio_preprocessing.py # Prétraitement audio
│   └── config.py              # Configuration transcription
│
├── ui/                        # Module interface utilisateur
│   ├── visualizer_app.py      # Application Qt6 PySide6
│   ├── manager.py             # Gestion processus visualizer
│   ├── assets/                # HTML, CSS, JS
│   └── config.py              # Configuration UI
│
├── api/                       # Module API REST
│   ├── server.py              # Serveur Flask + SSE
│   ├── routes/
│   │   ├── transcription.py   # Endpoints SSE
│   │   └── text_processing.py # Endpoints AutoGen (préparés)
│   └── config.py              # Configuration API
│
├── shared/                    # Utilitaires partagés
│   ├── config.py              # Configuration globale
│   ├── context.py             # État partagé
│   ├── hotkey.py              # Gestion hotkeys
│   └── sleep.py               # Gestion veille/actif
│
├── services/                  # Module AutoGen (à implémenter)
│   ├── README.md              # Guide intégration
│   └── config.py.example      # Exemple configuration
│
├── scripts/                   # Scripts de démarrage
│   ├── start_transcription.bat
│   ├── start_transcription_debug.bat
│   ├── stop_transcription.bat
│   └── run_enhanced.ps1
│
└── ARCHITECTURE.md            # Documentation détaillée
```

## Démarrage Rapide

### Lancement Normal
```bash
# Via Python
python main.py

# Via script Windows
scripts\start_transcription.bat

# Via PowerShell
scripts\run_enhanced.ps1
```

### Lancement Debug (Console visible)
```bash
scripts\start_transcription_debug.bat
```

### Arrêt
```bash
scripts\stop_transcription.bat
```

## Fonctionnalités

### Core (Transcription)
- ✅ Transcription en temps réel avec Whisper
- ✅ Prétraitement audio (filtre passe-haut, amplification, normalisation)
- ✅ Détection d'activité vocale (VAD)
- ✅ Modèle unique optimisé (large)
- ✅ Collage automatique au curseur
- ✅ Support GPU (CUDA) et CPU

### UI (Visualiseur)
- ✅ Visualisation forme d'onde en temps réel
- ✅ Affichage preview transcription
- ✅ Fenêtre toujours au premier plan
- ✅ Interface Qt6 moderne
- ✅ Pas de prise de focus (non-intrusif)

### API (Communication)
- ✅ Server-Sent Events pour transcription temps réel
- ✅ Endpoints REST
- ✅ CORS activé
- ✅ Endpoints préparés pour AutoGen

### Shared (Utilitaires)
- ✅ Hotkey F9 pour veille/actif
- ✅ Auto-veille après 10s d'inactivité
- ✅ Veille profonde après 10 min (décharge modèles)
- ✅ Configuration centralisée

## Configuration

Tous les paramètres sont configurables dans les modules :
- **core/config.py** : Modèles, audio, transcription
- **ui/config.py** : Visualiseur
- **api/config.py** : Serveur API (port, host)
- **shared/config.py** : Global (hotkey, sleep)

## Intégration AutoGen (Futur)

Le projet est préparé pour intégrer AutoGen pour reformulation de texte :

### Étapes
1. Installer AutoGen : `pip install pyautogen`
2. Copier `services/config.py.example` → `services/config.py`
3. Configurer clés API (OpenAI, Claude, ou LLM local)
4. Créer agents dans `services/agents/`
5. Activer endpoints dans `api/routes/text_processing.py`
6. Ajouter boutons UI dans visualiseur

### Endpoints Préparés
- `POST /api/reformulate/prompt` - Optimisation prompts IA
- `POST /api/reformulate/email` - Formatage emails
- `POST /api/reformulate/summary` - Résumé de texte

Voir [services/README.md](services/README.md) pour guide complet.

## Architecture Technique

### Communication Inter-Modules
```
┌─────────┐         ┌─────────┐
│   UI    │◄────────┤   API   │
│(Visual) │   SSE   │ (Flask) │
└─────────┘         └────┬────┘
                         │
                    ┌────┴────┐
                    │  Core   │
                    │(Whisper)│
                    └─────────┘
```

### Flow de Transcription
1. **Capture** : Audio capturé via sounddevice
2. **Prétraitement** : Filtre passe-haut + normalisation
3. **Détection** : VAD détecte la parole
4. **Transcription** : Whisper large (GPU/CPU)
5. **Preview** : Envoyé via SSE au visualiseur
6. **Production** : Collé au curseur après silence

## Technologies

- **Python 3.12+**
- **Whisper** (faster-whisper) - Transcription
- **PySide6** (Qt6) - Interface graphique
- **Flask** - Serveur API REST
- **sounddevice** - Capture audio
- **pynput** - Hotkeys et presse-papier

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture détaillée
- [services/README.md](services/README.md) - Guide AutoGen

## Licence

Ce projet est un outil personnel de transcription audio.
