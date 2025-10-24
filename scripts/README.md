# Scripts de Démarrage et d'Arrêt

Ce dossier contient tous les scripts pour démarrer et arrêter le système de transcription audio v2.0.

## Vue d'ensemble

Le système est composé de 3 modules principaux qui démarrent tous ensemble :
- **Core** : Module de transcription (Whisper, audio processing)
- **API** : Serveur Flask REST avec Server-Sent Events
- **UI** : Visualiseur d'ondes audio (Qt6/PySide6)

## Scripts Disponibles

### Windows Batch (.bat)

#### 🚀 start_transcription.bat
**Démarrage en arrière-plan (production)**

Lance le système complet en mode daemon (sans console visible).

```batch
scripts\start_transcription.bat
```

**Fonctionnalités** :
- ✅ Arrête les instances précédentes
- ✅ Vérifie l'environnement virtuel (.venv)
- ✅ Vérifie les dépendances (Flask, Whisper, PySide6)
- ✅ Vérifie la structure du projet (modules core/, ui/, api/)
- ✅ Démarre en arrière-plan (pythonw.exe)
- ✅ Messages clairs de progression

**Utilisation** :
```
[ETAPE 1/5] Arret des instances precedentes...
[ETAPE 2/5] Verification de l'environnement...
[ETAPE 3/5] Verification des dependances...
[ETAPE 4/5] Verification de la structure du projet...
[ETAPE 5/5] Demarrage du systeme...

Systeme demarre avec succes!
```

---

#### 🐛 start_transcription_debug.bat
**Démarrage en mode debug (développement)**

Lance le système avec console visible pour voir tous les logs.

```batch
scripts\start_transcription_debug.bat
```

**Fonctionnalités** :
- ✅ Toutes les vérifications de start_transcription.bat
- ✅ Console visible avec logs en temps réel
- ✅ Affiche tous les messages des modules (Core, API, UI)
- ✅ Permet de diagnostiquer les problèmes
- ⌨️ Ctrl+C pour arrêter

**Utilisation** :
```
MODE DEBUG - Console Visible

Ce mode affiche tous les logs en temps reel:
  - Messages du module CORE (transcription)
  - Messages du module API (serveur Flask)
  - Messages du module UI (visualiseur)
  - Erreurs et warnings detailles

Appuyez sur Ctrl+C pour arreter l'application.
```

---

#### 🛑 stop_transcription.bat
**Arrêt de tous les modules**

Arrête proprement tous les processus du système.

```batch
scripts\stop_transcription.bat
```

**Fonctionnalités** :
- ✅ Arrête le module CORE (main.py)
- ✅ Arrête le module UI (visualizer)
- ✅ Arrête le module API (Flask)
- ✅ Vérifie qu'aucun processus ne reste actif
- ✅ Nettoyage forcé si nécessaire

**Utilisation** :
```
[1/3] Arret du module CORE (main.py)...
[2/3] Arret du module UI (visualizer)...
[3/3] Arret du module API (Flask)...

Arret termine - Tous les modules arretes

Modules arretes:
  - Core (transcription)
  - UI (visualizer)
  - API (serveur Flask)
```

---

### PowerShell (.ps1)

#### 🚀 run_enhanced.ps1
**Démarrage avec PowerShell**

Équivalent de start_transcription_debug.bat mais pour PowerShell.

```powershell
.\scripts\run_enhanced.ps1
```

**Fonctionnalités** :
- ✅ Toutes les vérifications (environnement, dépendances, structure)
- ✅ Messages colorisés (Cyan, Green, Yellow, Red)
- ✅ Console visible avec logs en temps réel
- ✅ Diagnostic complet avant démarrage
- ⌨️ Ctrl+C pour arrêter

**Note** : Vous devrez peut-être activer l'exécution de scripts PowerShell :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Workflow Recommandé

### Développement (Debug)
```batch
# Démarrer en mode debug
scripts\start_transcription_debug.bat

# Travailler et voir les logs...

# Arrêter avec Ctrl+C ou:
scripts\stop_transcription.bat
```

### Production (Daemon)
```batch
# Démarrer en arrière-plan
scripts\start_transcription.bat

# Travailler normalement...

# Arrêter quand terminé
scripts\stop_transcription.bat
```

---

## Vérifications Effectuées

Tous les scripts (sauf stop) vérifient automatiquement :

### 1. Environnement Virtuel
- ✅ Présence de `.venv\Scripts\python.exe`
- ✅ Version de Python

### 2. Dépendances Python
- ✅ Flask (serveur API)
- ✅ faster-whisper (transcription)
- ✅ PySide6 (interface Qt6)
- ✅ sounddevice (capture audio)

### 3. Structure du Projet
- ✅ `main.py` (point d'entrée)
- ✅ `core/` (module transcription)
- ✅ `ui/` (module interface)
- ✅ `api/` (module API)
- ✅ `shared/` (utilitaires)

### 4. Instances Précédentes
- ✅ Arrêt automatique des processus existants

---

## Dépannage

### Erreur : "Virtual environment introuvable"
**Solution** : Créez l'environnement virtuel :
```batch
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Erreur : "Module core/ introuvable"
**Solution** : Vérifiez que vous êtes dans le bon répertoire :
```batch
cd C:\GitHub\transcription-audio
dir  # Vous devez voir: core/, ui/, api/, main.py
```

### Erreur : "faster-whisper non installé"
**Solution** : Installez les dépendances :
```batch
.venv\Scripts\pip install -r requirements.txt
```

### Le système ne démarre pas
**Solution** : Utilisez le mode debug pour voir les erreurs :
```batch
scripts\start_transcription_debug.bat
# Lisez attentivement les messages d'erreur
```

### Le système ne s'arrête pas
**Solution** : Le script stop_transcription.bat force l'arrêt :
```batch
scripts\stop_transcription.bat
# Si ça ne suffit pas, tuez manuellement:
taskkill /F /IM pythonw.exe
```

---

## Notes Techniques

### Chemins Relatifs
Tous les scripts utilisent `cd /d "%~dp0\.."` pour se positionner dans le répertoire du projet, peu importe d'où vous les lancez.

### Processus Python
- `python.exe` : Console visible (debug)
- `pythonw.exe` : Pas de console (daemon)

### Modules Démarrés
Le fichier `main.py` démarre automatiquement :
1. Serveur API Flask (port 5432)
2. Module Core (transcription Whisper)
3. Module UI (visualiseur Qt6)

Tout est orchestré depuis un seul point d'entrée !

---

## Raccourcis Rapides

```batch
# Démarrer (daemon)
scripts\start_transcription.bat

# Démarrer (debug)
scripts\start_transcription_debug.bat

# Arrêter
scripts\stop_transcription.bat
```

Ou depuis PowerShell :
```powershell
.\scripts\run_enhanced.ps1
```
