# 🎤 Système de Dictée Vocale Avancé

Système de transcription vocale en temps réel avec preview dynamique et transcription finale haute qualité.

## 🚀 Démarrage rapide

```bash
.\run_enhanced.bat
```

Ou avec PowerShell :
```powershell
.\run_enhanced.ps1
```

## 📋 Fonctionnalités

- **Preview temps réel** : Affichage instantané sous forme d'onde avec transcription temporaire (modèle Medium)
- **Transcription finale** : Collage automatique de haute qualité avec contexte complet (modèle Large)
- **Visualisation audio** : Forme d'onde en temps réel avec indicateur SSE
- **Double buffering** : Fenêtre glissante pour preview + contexte complet pour production
- **Mode veille intelligent** : Veille auto après 10s d'inactivité, réactivation instantanée avec Alt+W

## ⚙️ Architecture

- **Modèle Preview** : `medium` (769M params, ~90-95% précision, 3s de contexte)
- **Modèle Production** : `large` (1550M params, ~95-98% précision, contexte complet)
- **Communication** : Server-Sent Events (SSE) sur port 5432
- **Visualizer** : PySide6 Qt WebEngine avec WaveSurfer.js

## 📦 Prérequis

- Python 3.12.4 (dans `.venv`)
- CUDA (pour GPU)
- Microphone

## 🎯 Utilisation

1. **Lancer** : `run_enhanced.bat`
2. **Parler** : Le visualizer affiche l'onde et le texte preview
3. **Pause** : Le texte final est collé automatiquement dans l'application active
4. **Veille** : Alt+W pour basculer veille/actif (ou ESC, ou fermer visualizer)
5. **Fermer** : Ctrl+C dans le terminal

### Raccourcis

| Touche | Action |
|--------|--------|
| **Alt+W** | Bascule veille/actif |
| **ESC** | Met en veille (dans visualizer) |
| **Espace** | Pause/reprend l'enregistrement |

Voir [MODE_VEILLE.md](MODE_VEILLE.md) pour plus de détails.

## 📁 Structure

```
transcription-audio/
├── main_enhanced.py           # Programme principal
├── mic_visualizer_enhanced.py # Visualizer Qt
├── run_enhanced.bat           # Script de lancement Windows
├── run_enhanced.ps1           # Script PowerShell
├── .venv/                     # Environnement virtuel Python
└── __pycache__/               # Cache Python
```

## ⚡ Performance

- **Preview** : 500-1200ms de latence (temps réel)
- **Production** : 2-3s de latence (haute qualité)
- **GPU** : CUDA requis pour performances optimales

## 🔧 Configuration

Modifiez les constantes dans `main_enhanced.py` :
- `PREVIEW_WINDOW_SECONDS` : Durée contexte preview (défaut: 3s)
- `ENERGY_THRESHOLD` : Seuil de détection vocale (défaut: 0.003)
- `SSE_PORT` : Port serveur SSE (défaut: 5432)

---

**Version** : Enhanced v2  
**Date** : Octobre 2025  
**Auteur** : Skeeder1
