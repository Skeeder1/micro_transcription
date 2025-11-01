# Démarrage rapide - Ubuntu

Guide ultra-rapide pour lancer le système de dictée vocale sur Ubuntu en 5 minutes.

## ⚡ Installation express

```bash
# 1. Installer les dépendances système
sudo apt update
sudo apt install -y python3 python3-pip python3-venv \
                    xdotool xclip xsel \
                    portaudio19-dev \
                    libxcb-xinerama0

# 2. Créer l'environnement virtuel
cd ~/projet/micro_transcription
python3 -m venv .venv
source .venv/bin/activate

# 3. Installer les dépendances Python
pip install --upgrade pip
pip install flask faster-whisper PySide6 pyperclip pynput numpy sounddevice

# 4. Tester l'installation
bash scripts/test_ubuntu_setup.sh

# 5. Lancer l'application
bash scripts/start_transcription_debug.sh
```

## 🎯 Utilisation basique

### Démarrer
```bash
bash scripts/start_transcription.sh        # Mode normal (arrière-plan)
bash scripts/start_transcription_debug.sh  # Mode debug (voir les logs)
```

### Arrêter
```bash
bash scripts/stop_transcription.sh
```

### Contrôles
- **F9** : Basculer veille/actif
- **Icône system tray** : Clic droit pour le menu

## 🔧 Configuration minimale

### Ajuster la sensibilité du micro
```python
# Éditer core/config.py
ENERGY_THRESHOLD = 0.01  # Plus bas = plus sensible
```

### Choisir un modèle plus rapide
```python
# Éditer core/config.py
WHISPER_MODEL = "medium"  # Au lieu de "large"
```

### Désactiver le system tray
```python
# Éditer shared/config.py
ENABLE_SYSTEM_TRAY = False
```

## 📝 Notes importantes

1. **Première exécution** : Le chargement des modèles Whisper peut prendre 1-2 minutes
2. **GPU NVIDIA** : Si vous avez une carte NVIDIA, installez CUDA pour accélérer la transcription
3. **Wayland** : Sous Wayland, xdotool peut avoir des limitations. Le fallback automatique sera utilisé.
4. **GNOME** : Installez l'extension appindicator pour voir l'icône system tray :
   ```bash
   sudo apt install gnome-shell-extension-appindicator
   gnome-extensions enable ubuntu-appindicators@ubuntu.com
   ```

## 🆘 Problèmes courants

### Le micro n'est pas détecté
```bash
python3 -c "import sounddevice as sd; print(sd.query_devices())"
```

### Le collage ne fonctionne pas
```bash
# Vérifier xdotool
which xdotool
xdotool type "test"
```

### L'interface ne s'ouvre pas
```bash
# Vérifier les logs
tail -f /tmp/transcription_*.log
```

## 📚 Documentation complète

- **Installation détaillée** : `docs/INSTALL_UBUNTU.md`
- **Changements Ubuntu** : `docs/UBUNTU_CHANGES.md`
- **Architecture générale** : `ARCHITECTURE.md` (racine du projet)

## ✅ Checklist de validation

Après l'installation, vérifiez que :
- [ ] Le script de test réussit : `bash scripts/test_ubuntu_setup.sh`
- [ ] Le visualiseur s'ouvre
- [ ] L'icône system tray apparaît (si GNOME avec extension)
- [ ] Le microphone capture l'audio
- [ ] La transcription s'affiche dans le visualiseur
- [ ] Le texte se colle correctement (Ctrl+V automatique)
- [ ] F9 bascule bien en mode veille

## 🎉 C'est parti !

Une fois tout installé, parlez dans votre micro et regardez la transcription apparaître en temps réel dans le visualiseur. Le texte sera automatiquement collé dans l'application active après un moment de silence.

**Astuce** : Testez d'abord avec des phrases courtes pour vous habituer au système !
