# Installation et Configuration - Ubuntu Linux

Guide complet pour installer et configurer le système de dictée vocale sur Ubuntu.

## 📋 Prérequis

- **Ubuntu** : 20.04 LTS ou supérieur (testé sur 22.04 et 24.04)
- **Python** : 3.8 ou supérieur
- **Environnement graphique** : X11 ou Wayland
- **Audio** : Microphone fonctionnel
- **GPU (optionnel)** : NVIDIA avec CUDA pour accélération Whisper

## 🚀 Installation rapide

### 1. Installer les dépendances système

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Python et outils de développement
sudo apt install -y python3 python3-pip python3-venv

# Dépendances audio (PortAudio pour sounddevice)
sudo apt install -y portaudio19-dev python3-pyaudio

# Outils pour le collage de texte (OBLIGATOIRE)
sudo apt install -y xdotool xclip xsel

# Bibliothèques Qt pour l'interface graphique
sudo apt install -y libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
                    libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
                    libxcb-shape0 libxcb-xfixes0 libxcb-xkb1

# Optionnel : ImageMagick pour conversion d'icônes
sudo apt install -y imagemagick
```

### 2. Cloner et configurer le projet

```bash
# Cloner le dépôt (ou extraire l'archive)
cd ~/projet
# git clone <votre-repo> micro_transcription
cd micro_transcription

# Créer l'environnement virtuel Python
python3 -m venv .venv

# Activer l'environnement virtuel
source .venv/bin/activate

# Installer les dépendances Python
pip install --upgrade pip
pip install flask faster-whisper PySide6 pyperclip pynput numpy sounddevice

# Optionnel : installer les dépendances pour la détection vocale avancée
pip install torch torchaudio onnxruntime  # Pour Silero VAD
```

### 3. Configurer les permissions audio

```bash
# Ajouter l'utilisateur au groupe audio
sudo usermod -aG audio $USER

# Redémarrer la session (logout/login) pour appliquer les changements
# Ou redémarrer le système
```

### 4. Tester l'installation

```bash
# Lancer en mode debug pour voir les logs
bash scripts/start_transcription_debug.sh
```

Si tout fonctionne, vous devriez voir :
- Le serveur API démarrer
- Le visualiseur s'ouvrir
- Les modèles Whisper se charger
- L'icône system tray apparaître (si supporté)

## 🎯 Utilisation

### Lancement normal

```bash
# Démarrer l'application en arrière-plan
bash scripts/start_transcription.sh

# Vérifier les logs
tail -f /tmp/transcription_*.log
```

### Mode debug

```bash
# Lancer avec logs visibles dans le terminal
bash scripts/start_transcription_debug.sh
```

### Arrêt

```bash
# Arrêter proprement tous les processus
bash scripts/stop_transcription.sh
```

### Raccourcis clavier

- **F9** : Bascule veille/actif (pause la transcription)
- **Ctrl+C** : Arrêter l'application (en mode debug)

### System Tray (barre système)

Si votre environnement de bureau le supporte, une icône apparaît dans la barre système avec :
- 🎤 État actuel (actif/veille)
- 💤 Basculer veille/actif
- 👁️ Afficher le visualiseur
- ❌ Quitter l'application

## ⚙️ Configuration avancée

### Service systemd (démarrage automatique)

Pour lancer l'application automatiquement au démarrage :

```bash
# Copier le fichier service
cp scripts/transcription.service ~/.config/systemd/user/

# Éditer le fichier pour ajuster les chemins (remplacer %h/projet/micro_transcription)
nano ~/.config/systemd/user/transcription.service

# Recharger systemd
systemctl --user daemon-reload

# Activer le service
systemctl --user enable transcription.service

# Démarrer le service
systemctl --user start transcription.service

# Vérifier le statut
systemctl --user status transcription.service

# Voir les logs
journalctl --user -u transcription.service -f
```

### Désactiver le system tray

Si vous ne souhaitez pas l'icône dans la barre système :

```python
# Éditer shared/config.py
ENABLE_SYSTEM_TRAY = False
```

### Configurer le seuil de détection vocale

Si la détection est trop sensible ou pas assez :

```python
# Éditer core/config.py
ENERGY_THRESHOLD = 0.01  # Diminuer = plus sensible, augmenter = moins sensible

# Mode debug pour calibrer
DEBUG_AUDIO_LEVEL = True  # Affiche les niveaux RMS en temps réel
```

### Changer le modèle Whisper

```python
# Éditer core/config.py
WHISPER_MODEL = "medium"  # Choix : tiny, base, small, medium, large

# tiny    : ~75 MB  - Très rapide, moins précis
# base    : ~150 MB - Rapide, précision correcte
# small   : ~500 MB - Bon compromis
# medium  : ~1.5 GB - Très précis
# large   : ~3 GB   - Maximum de précision (par défaut)
```

## 🐛 Dépannage

### Le microphone n'est pas détecté

```bash
# Lister les périphériques audio disponibles
python3 -c "import sounddevice as sd; print(sd.query_devices())"

# Tester la capture audio
python3 -c "import sounddevice as sd; import numpy as np; print('Recording 3s...'); sd.rec(3*16000, samplerate=16000, channels=1); sd.wait(); print('OK')"
```

### Le collage (Ctrl+V) ne fonctionne pas

**Sur X11** :
```bash
# Vérifier que xdotool est installé
which xdotool

# Tester manuellement
xdotool type "test"
```

**Sur Wayland** :
```bash
# Installer ydotool (alternative pour Wayland)
sudo apt install ydotool

# Note : xdotool a des limitations sous Wayland
# Le fallback pynput sera utilisé automatiquement
```

### L'interface graphique ne s'affiche pas

```bash
# Vérifier les variables d'environnement
echo $DISPLAY
echo $WAYLAND_DISPLAY

# Tester Qt
python3 -c "from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); print('Qt OK')"
```

### Le system tray n'apparaît pas

Certains environnements de bureau ne supportent pas les system tray :

- ✅ **GNOME** (avec extension appindicator) : `sudo apt install gnome-shell-extension-appindicator`
- ✅ **KDE Plasma** : Support natif
- ✅ **XFCE** : Support natif
- ✅ **MATE** : Support natif
- ⚠️ **GNOME vanilla** : Nécessite extension
- ❌ **Certains gestionnaires minimalistes** : Non supporté

Pour GNOME :
```bash
# Installer l'extension
sudo apt install gnome-shell-extension-appindicator

# Activer l'extension
gnome-extensions enable ubuntu-appindicators@ubuntu.com

# Redémarrer GNOME Shell : Alt+F2, puis taper 'r', puis Entrée
```

### Erreur "No module named 'faster_whisper'"

```bash
# Réactiver l'environnement virtuel
source .venv/bin/activate

# Réinstaller faster-whisper
pip install --upgrade faster-whisper
```

### Erreur CUDA / GPU non détecté

Si vous avez un GPU NVIDIA mais qu'il n'est pas utilisé :

```bash
# Vérifier CUDA
nvidia-smi

# Installer PyTorch avec support CUDA
pip install torch --index-url https://download.pytorch.org/whl/cu118

# Vérifier dans les logs que CUDA est détecté
# Vous devriez voir : "Device: cuda" au lieu de "Device: cpu"
```

### Les logs ne s'affichent pas

```bash
# Les logs sont dans /tmp
ls -lah /tmp/transcription_*.log

# Voir les logs en temps réel
tail -f /tmp/transcription_*.log

# Nettoyer les vieux logs (>7 jours)
find /tmp -name "transcription_*.log" -mtime +7 -delete
```

## 🔧 Optimisation des performances

### Mode CPU uniquement

Si vous n'avez pas de GPU NVIDIA :

```python
# Éditer core/config.py
DEVICE = "cpu"
WHISPER_MODEL = "medium"  # Utiliser un modèle plus petit
```

### Réduire l'utilisation mémoire

```python
# Éditer core/config.py
WHISPER_MODEL = "small"        # Modèle plus léger
MODEL_NUM_WORKERS = 1          # Réduire le parallélisme
FLOAT_PRECISION = "int8"       # Quantification (moins précis mais plus rapide)
```

### Accélérer la transcription

```python
# Éditer core/config.py
BEAM_SIZE = 1                  # Désactiver beam search (moins précis mais plus rapide)
VAD_FILTER = True              # Activer le filtre de détection vocale
PREVIEW_UPDATE_INTERVAL = 1.5  # Réduire la fréquence des previews
```

## 📚 Ressources supplémentaires

- **Faster-Whisper** : https://github.com/guillaumekln/faster-whisper
- **PySide6 documentation** : https://doc.qt.io/qtforpython/
- **xdotool manuel** : `man xdotool`
- **Systemd user services** : `man systemd.service`

## 🆘 Support

Si vous rencontrez des problèmes :

1. Vérifiez les logs : `tail -f /tmp/transcription_*.log`
2. Lancez en mode debug : `bash scripts/start_transcription_debug.sh`
3. Vérifiez les dépendances : `bash scripts/start_transcription_debug.sh` (étape 3 et 4)
4. Consultez les issues GitHub du projet

## 🎉 Félicitations !

Votre système de dictée vocale est maintenant configuré sur Ubuntu. Profitez de la transcription en temps réel !

**Astuce** : Testez d'abord avec des phrases courtes pour vous familiariser avec le délai de transcription et le comportement du système.
