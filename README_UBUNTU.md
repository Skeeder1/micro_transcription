# 🐧 Support Ubuntu Linux

Votre système de dictée vocale est maintenant **entièrement compatible Ubuntu** ! 🎉

## ✨ Qu'est-ce qui est nouveau ?

### 🚀 Démarrage rapide Ubuntu
```bash
# Installation en 3 commandes
sudo apt install -y python3 python3-venv xdotool xclip portaudio19-dev
python3 -m venv .venv && source .venv/bin/activate
pip install flask faster-whisper PySide6 pyperclip pynput sounddevice

# Lancer l'application
bash scripts/start_transcription.sh
```

### 🎨 System Tray (Nouvelle fonctionnalité)
Une **icône dans la barre système** avec menu pour contrôler l'application :
- 🎤 État actuel (actif/veille)
- 💤 Basculer veille/actif
- 👁️ Afficher le visualiseur
- ❌ Quitter

### 🔧 Collage intelligent
Auto-détection de votre environnement (X11/Wayland) et choix automatique du meilleur outil :
- **X11** : Utilise `xdotool` natif (ultra fiable)
- **Wayland** : Fallback automatique sur pynput
- **Windows** : Fonctionne comme avant (100% compatible)

### 📜 Scripts shell natifs
Équivalents de vos scripts `.bat` Windows :
- `scripts/start_transcription.sh` - Lancement normal
- `scripts/start_transcription_debug.sh` - Mode debug
- `scripts/stop_transcription.sh` - Arrêt propre
- `scripts/test_ubuntu_setup.sh` - Test installation

### ⚙️ Service systemd (optionnel)
Démarrage automatique au boot :
```bash
cp scripts/transcription.service ~/.config/systemd/user/
systemctl --user enable --now transcription.service
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[QUICKSTART_UBUNTU.md](docs/QUICKSTART_UBUNTU.md)** | Démarrage rapide (5 min) |
| **[INSTALL_UBUNTU.md](docs/INSTALL_UBUNTU.md)** | Guide complet installation |
| **[UBUNTU_CHANGES.md](docs/UBUNTU_CHANGES.md)** | Détails techniques des changements |
| **[CHANGELOG_UBUNTU.md](CHANGELOG_UBUNTU.md)** | Historique des modifications |

## 🎯 Utilisation

### Tester votre installation
```bash
bash scripts/test_ubuntu_setup.sh
```

### Lancer l'application
```bash
# Mode normal (arrière-plan)
bash scripts/start_transcription.sh

# Mode debug (voir les logs)
bash scripts/start_transcription_debug.sh
```

### Arrêter l'application
```bash
bash scripts/stop_transcription.sh
```

### Contrôles
- **F9** : Basculer veille/actif
- **Clic droit sur l'icône tray** : Menu de contrôle
- **Ctrl+C** (mode debug) : Arrêter

## 🔧 Configuration rapide

### Ajuster la sensibilité du micro
```python
# Éditer core/config.py
ENERGY_THRESHOLD = 0.01  # Plus bas = plus sensible
```

### Désactiver le system tray
```python
# Éditer shared/config.py
ENABLE_SYSTEM_TRAY = False
```

### Choisir un modèle Whisper plus rapide
```python
# Éditer core/config.py
WHISPER_MODEL = "medium"  # Au lieu de "large"
```

## 🆘 Aide rapide

### Le micro ne fonctionne pas
```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

### Le collage ne marche pas
```bash
which xdotool  # Doit retourner un chemin
xdotool type "test"  # Doit taper "test"
```

### L'icône system tray n'apparaît pas (GNOME)
```bash
sudo apt install gnome-shell-extension-appindicator
gnome-extensions enable ubuntu-appindicators@ubuntu.com
```

### Voir les logs
```bash
tail -f /tmp/transcription_*.log
```

## ✅ Compatibilité

| Plateforme | Support | Notes |
|------------|---------|-------|
| **Ubuntu 20.04+** | ✅ Complet | Testé sur 24.04 |
| **Debian 11+** | ✅ Probable | Non testé officiellement |
| **Fedora** | ⚠️ Probable | Remplacer `apt` par `dnf` |
| **Arch Linux** | ⚠️ Probable | Remplacer `apt` par `pacman` |
| **Windows** | ✅ Complet | 100% compatible, aucune régression |

### Environnements graphiques

| DE | Support | System Tray |
|----|---------|-------------|
| **GNOME** | ✅ | ✅ (avec extension) |
| **KDE Plasma** | ✅ | ✅ Natif |
| **XFCE** | ✅ | ✅ Natif |
| **MATE** | ✅ | ✅ Natif |
| **Wayland** | ⚠️ | ⚠️ Limitations xdotool |

## 📊 Qu'est-ce qui a changé ?

### Fichiers modifiés
- `core/audio_capture.py` - Collage multi-plateforme
- `ui/manager.py` - Gestion subprocess Linux
- `core/engine.py` - Intégration system tray
- `shared/config.py` - Nouveau paramètre ENABLE_SYSTEM_TRAY

### Fichiers créés
**Code Python :**
- `ui/system_tray.py` - Gestionnaire system tray
- `ui/assets/tray_icon.svg` - Icône personnalisée

**Scripts shell :**
- 4 scripts `.sh` pour Ubuntu

**Documentation :**
- 4 guides complets

**Total :** ~600 lignes de code ajoutées, 0 dépendance Python nouvelle

## 🎉 Prêt à utiliser !

Votre système de transcription fonctionne maintenant **aussi bien sur Ubuntu que sur Windows** !

```bash
# Test rapide
bash scripts/test_ubuntu_setup.sh

# C'est parti !
bash scripts/start_transcription_debug.sh
```

**Astuce :** Commencez par le mode debug pour voir ce qui se passe en temps réel, puis passez au mode normal une fois que tout fonctionne.

---

💡 **Besoin d'aide ?** Consultez [INSTALL_UBUNTU.md](docs/INSTALL_UBUNTU.md) pour le guide complet avec dépannage détaillé.
