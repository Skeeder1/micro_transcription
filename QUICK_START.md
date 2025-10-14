# 🚀 Installation Rapide - Système de Dictée Avancé

## Étape 1 : Installer Flask dans le venv

```bash
# Dans le dossier du projet
cd C:\GitHub\transcription-audio

# Installer Flask DANS le venv (important!)
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -m pip install flask

# OU utiliser le chemin relatif
.\.venv\Scripts\python.exe -m pip install flask
```

**Important** : Utilisez toujours le Python du venv, pas le Python système !

## Étape 2 : Vérifier les dépendances dans le venv

```bash
# Utiliser le Python du venv pour vérifier
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "from flask import Flask; print('✅ Flask OK')"
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "from faster_whisper import WhisperModel; print('✅ Whisper OK')"
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "from PySide6.QtWebEngineWidgets import QWebEngineView; print('✅ Qt OK')"
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "import sounddevice; print('✅ sounddevice OK')"
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "import keyboard; print('✅ keyboard OK')"
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -c "import pyperclip; print('✅ pyperclip OK')"
```

Si une dépendance manque :
```bash
C:\GitHub\transcription-audio\.venv\Scripts\python.exe -m pip install PySide6 sounddevice numpy faster-whisper keyboard pyperclip
```

## Étape 3 : Tester le serveur SSE

**Méthode 1 : Script automatique (recommandé)**
```bash
# Double-cliquez sur ce fichier ou exécutez :
run_enhanced.bat

# Ou avec PowerShell :
.\run_enhanced.ps1
```

**Méthode 2 : Lancement manuel**
```bash
# Utiliser le Python du venv
C:\GitHub\transcription-audio\.venv\Scripts\python.exe main_enhanced.py
```

**Attendu** :
```
======================================================================
🎤 SYSTÈME DE DICTÉE VOCALE AVANCÉ
======================================================================
📥 Chargement modèle PREVIEW (base)...
📥 Chargement modèle PRODUCTION (large)...
✅ Modèles chargés
🌐 Serveur SSE démarré sur http://127.0.0.1:5432
🎙️ Écoute active... (Ctrl+C pour quitter)
   💬 Preview → Visualizer (temps réel)
   📋 Production → Presse-papiers (haute qualité)
```

**Visualizer** devrait s'ouvrir automatiquement avec :
- Waveform animée
- Preview text zone en bas
- Indicateur SSE vert (connecté)

## Étape 4 : Tester

1. **Parlez dans le micro**
   - Regardez le visualizer
   - Preview doit apparaître en <500ms dans la zone texte
   - Waveform doit bouger

2. **Faites une pause de 1.5s**
   - Preview disparaît
   - Texte final collé dans application active (ex: Notepad)
   - Console affiche : `📋 [votre texte]`

3. **Continuez à parler**
   - Nouveau cycle commence

## ✅ Checklist de validation

- [ ] Flask installé
- [ ] `python main_enhanced.py` démarre sans erreur
- [ ] Visualizer s'ouvre
- [ ] Indicateur SSE est vert
- [ ] Waveform bouge quand je parle
- [ ] Preview s'affiche en temps réel
- [ ] Texte final collé correctement
- [ ] Ctrl+C arrête tout proprement

## 🐛 Si problème

### Erreur : `ModuleNotFoundError: No module named 'flask'`
```bash
pip install flask
```

### Erreur : `ModuleNotFoundError: No module named 'werkzeug'`
```bash
pip install werkzeug
```

### Visualizer ne s'ouvre pas
```bash
# Tester manuellement
python mic_visualizer_enhanced.py 5432
```

### SSE ne se connecte pas (pastille grise)
```bash
# Dans un navigateur, ouvrir :
http://127.0.0.1:5432/ping

# Doit afficher "pong"
# Si erreur, vérifier que main_enhanced.py tourne
```

### Preview ne s'affiche pas
- Vérifier console Python : logs `[SSE] Received:` doivent apparaître
- Vérifier console JS dans terminal : `[SSE] Connected`
- Ouvrir DevTools navigateur si possible (F12)

## 📝 Fichiers créés

```
c:\GitHub\transcription-audio\
├── main_enhanced.py              ← Script principal (nouveau)
├── mic_visualizer_enhanced.py    ← Visualizer avec preview (nouveau)
├── ADVANCED_DICTATION_SYSTEM.md  ← Documentation complète (nouveau)
├── QUICK_START.md                ← Ce fichier (nouveau)
├── main.py                       ← Version simple (ancien)
└── mic_visualizer.py             ← Visualizer simple (ancien)
```

## 🎯 Prêt !

Si toutes les étapes fonctionnent, vous avez maintenant :
- ✅ Preview temps réel (<500ms)
- ✅ Transcription finale haute qualité
- ✅ Visualizer professionnel
- ✅ Double modèle Whisper (base + large)
- ✅ Communication SSE

**Enjoy!** 🚀
