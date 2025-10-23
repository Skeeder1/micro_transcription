# 🎤 Système de Dictée Vocale Avancé

Application de transcription vocale en temps réel avec visualiseur d'ondes indépendant.

## 🌟 Caractéristiques

- 🎯 **Transcription en temps réel** avec Whisper (modèle large)
- 📊 **Visualiseur d'ondes** indépendant avec interface web
- 💤 **Mode veille automatique** après inactivité
- 🔄 **Preview en temps réel** + transcription finale
- 🎚️ **Prétraitement audio** (filtre passe-haut, amplification, normalisation)
- 🌐 **API REST** pour contrôle à distance du visualiseur
- ⌨️ **Raccourci clavier** (F9) pour basculer veille/actif

## 📦 Architecture

```
transcription-audio/
├── transcription_app/       # Application de transcription vocale
│   ├── app.py              # Point d'entrée principal
│   ├── config.py           # Configuration
│   ├── models.py           # Gestion des modèles Whisper
│   ├── audio.py            # Capture et traitement audio
│   ├── main_loop.py        # Boucle principale
│   ├── sleep.py            # Gestion mode veille
│   └── ...
├── visualizer/             # Visualiseur web indépendant
│   ├── app.py             # Serveur Flask avec API REST
│   ├── client.py          # Client HTTP Python
│   ├── server.py          # Launcher du serveur
│   ├── templates/         # Interface web HTML
│   └── static/            # Assets CSS/JS
├── run_visualizer.py      # Script de démarrage du visualiseur
├── test_visualizer.py     # Tests du visualiseur
└── main_enhanced.py       # Point d'entrée de l'application
```

## 🚀 Installation

### Prérequis

- Python 3.8+
- CUDA (optionnel, pour GPU NVIDIA)
- Microphone

### Dépendances

```bash
# Dépendances principales
pip install faster-whisper sounddevice numpy scipy pynput pyperclip

# Dépendances du visualiseur (OBLIGATOIRE)
pip install -r visualizer/requirements.txt
```

**⚠️ IMPORTANT**: Les dépendances du visualiseur (`flask-cors`, etc.) sont **obligatoires** pour que le système fonctionne. Sans elles, le visualiseur ne démarrera pas.

## 🎬 Démarrage Rapide

### Avec Visualiseur (Recommandé)

```bash
# Terminal 1: Démarrer le visualiseur
python run_visualizer.py

# Terminal 2: Démarrer l'application de transcription
python main_enhanced.py
```

Puis ouvrez votre navigateur à `http://127.0.0.1:5500` pour voir le visualiseur.

### Sans Visualiseur

```bash
# L'application fonctionne aussi sans visualiseur
python main_enhanced.py
```

## ⚙️ Configuration

Éditez `transcription_app/config.py` pour personnaliser:

```python
# Activer/désactiver la transcription
ENABLE_TRANSCRIPTION = True

# Activer/désactiver la preview en temps réel
ENABLE_PREVIEW = True

# Activer/désactiver la transcription finale
ENABLE_PRODUCTION = True

# Modèle Whisper
WHISPER_MODEL = "large"

# Périphérique de calcul
DEVICE = "cuda"  # ou "cpu"

# Seuil d'énergie pour détecter la parole
ENERGY_THRESHOLD = 0.003

# Délai d'inactivité avant veille automatique (secondes)
AUTO_SLEEP_SECONDS = 10.0

# Port du visualiseur
SSE_PORT = 5500
```

## 🎮 Utilisation

### Raccourcis Clavier

- **F9**: Basculer entre mode actif et mode veille

### Modes de Fonctionnement

#### Mode Actif
- L'application écoute et transcrit en continu
- Preview affichée dans le visualiseur
- Transcription finale collée au curseur après silence

#### Mode Veille
- L'application cesse de transcrire
- Économise les ressources
- Réactivation rapide avec F9

#### Mode Veille Profonde (automatique après 10 min)
- Décharge les modèles IA de la RAM
- Consommation minimale
- Rechargement des modèles à la réactivation (~3-5s)

## 🌐 Visualiseur Web Indépendant

Le visualiseur fonctionne comme un service web indépendant avec API REST.

### Démarrage

```bash
# Port par défaut (5500)
python run_visualizer.py

# Port personnalisé
python run_visualizer.py 8080

# Host et port personnalisés
python run_visualizer.py 8080 0.0.0.0
```

### API REST

Le visualiseur expose une API REST complète:

```bash
# Envoyer du texte de preview
curl -X POST http://127.0.0.1:5500/api/preview \
  -H "Content-Type: application/json" \
  -d '{"text": "Transcription en cours..."}'

# Changer l'état (active/sleep)
curl -X POST http://127.0.0.1:5500/api/state \
  -H "Content-Type: application/json" \
  -d '{"state": "sleep"}'

# Récupérer le statut
curl http://127.0.0.1:5500/api/status

# Healthcheck
curl http://127.0.0.1:5500/ping
```

### Client Python

```python
from visualizer.client import VisualizerClient

viz = VisualizerClient()
viz.send_preview("Hello world")
viz.set_state("sleep")
status = viz.get_status()
```

## 🧪 Tests

```bash
# Tester le visualiseur
python test_visualizer.py

# Tester les exemples d'utilisation
python -m visualizer.example_usage
```

## 📚 Documentation

- **[Architecture](ARCHITECTURE.md)** - Architecture détaillée du système
- **[Documentation Visualiseur](visualizer/README.md)** - Documentation complète du visualiseur

## 🔧 Fonctionnalités Avancées

### Prétraitement Audio

L'application applique automatiquement un prétraitement audio pour améliorer la qualité de transcription:

- **Filtre passe-haut** (80 Hz) - Supprime les bruits de fond basse fréquence
- **Amplification** (1.5x) - Améliore les voix faibles
- **Normalisation** - Standardise le volume

### Paramètres Whisper Optimisés

Configuration optimale pour transcription en français:

```python
LANGUAGE = "fr"
BEAM_SIZE = 8              # Meilleure qualité avec GPU
VAD_FILTER = True          # Ignore les segments sans parole
CONDITION_ON_PREVIOUS = True  # Meilleure cohérence
BEST_OF = 4                # Évalue plusieurs candidats
TEMPERATURE = 0.0          # Déterministe et précis
```

### Mode Visualiseur Uniquement

Vous pouvez utiliser le visualiseur seul sans transcription:

```python
# Dans config.py
ENABLE_TRANSCRIPTION = False
```

L'application affichera uniquement les ondes audio en temps réel.

## 🐛 Dépannage

### Le visualiseur ne se connecte pas
```bash
# Vérifier que le visualiseur est démarré
python run_visualizer.py

# Tester la connexion
python test_visualizer.py
```

### Erreur de chargement des modèles
```bash
# Vérifier les dépendances
pip install faster-whisper

# Essayer avec CPU si GPU pose problème
# Dans config.py: DEVICE = "cpu"
```

### Pas de détection audio
```bash
# Vérifier les périphériques audio
python -c "import sounddevice as sd; print(sd.query_devices())"

# Ajuster le seuil d'énergie dans config.py
ENERGY_THRESHOLD = 0.001  # Plus sensible
```

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment contribuer:

1. Fork le projet
2. Créer une branche (`git checkout -b feature/amazing-feature`)
3. Commit vos changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🙏 Remerciements

- [Faster Whisper](https://github.com/guillaumekln/faster-whisper) - Moteur de transcription
- [WaveSurfer.js](https://wavesurfer-js.org/) - Visualisation d'ondes
- [Flask](https://flask.palletsprojects.com/) - Framework web

## 📞 Support

Pour toute question ou problème, consultez:
- [Architecture](ARCHITECTURE.md)
- [Documentation Visualiseur](visualizer/README.md)
