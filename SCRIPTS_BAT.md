# 🚀 Scripts de Démarrage

Ce dossier contient **4 scripts `.bat`** pour lancer et gérer le système de transcription vocale :

## 📁 Fichiers disponibles

### 1️⃣ `start.bat` - **Système Complet** ⭐ (Recommandé)
Lance automatiquement **visualiseur + transcription** ensemble.

```batch
start.bat
```

**Ce qu'il fait :**
- 🧹 Nettoie toutes les instances existantes
- ✅ Lance le visualiseur (fenêtre native)
- ✅ Lance l'application de transcription
- ✅ Nettoie automatiquement à l'arrêt

**Quand l'utiliser :**
- Usage normal quotidien
- Première utilisation
- Quand vous voulez tout en un clic

---

### 2️⃣ `start_visualizer.bat` - **Visualiseur Seul**
Lance uniquement la fenêtre de visualisation audio.

```batch
start_visualizer.bat
```

**Ce qu'il fait :**
- 🧹 Ferme les visualiseurs existants
- ✅ Affiche la fenêtre de monitoring audio
- ✅ Toujours au premier plan
- ✅ Se masque en mode veille

**Quand l'utiliser :**
- Debugging du visualiseur
- Test de l'interface
- Si vous lancez la transcription manuellement

---

### 3️⃣ `start_transcription.bat` - **Transcription Seule**
Lance uniquement l'application de transcription.

```batch
start_transcription.bat
```

**Ce qu'il fait :**
- 🧹 Ferme les applications de transcription existantes
- ✅ Lance le système de transcription
- ✅ Gère le hotkey F9
- ✅ Met à jour l'état partagé

**Quand l'utiliser :**
- Pas besoin du visualiseur
- Mode console uniquement
- Debugging de la transcription

---

### 4️⃣ `stop_all.bat` - **Arrêt Complet** 🛑
Arrête toutes les instances en cours d'exécution.

```batch
stop_all.bat
```

**Ce qu'il fait :**
- 🛑 Ferme tous les visualiseurs
- 🛑 Ferme toutes les transcriptions
- 🧹 Nettoyage complet

**Quand l'utiliser :**
- Si les processus ne s'arrêtent pas normalement
- Avant de redémarrer le système
- Pour forcer l'arrêt de toutes les instances

---

## ⌨️ Commandes communes

| Touche | Action |
|--------|--------|
| **F9** | Basculer entre mode actif / veille |
| **ESC** | Fermer le visualiseur (visualiseur seul) |
| **Ctrl+C** | Arrêter la transcription |

---

## 📊 Tableau comparatif

| Fonctionnalité | `start.bat` | `start_visualizer.bat` | `start_transcription.bat` | `stop_all.bat` |
|----------------|:-----------:|:----------------------:|:-------------------------:|:--------------:|
| Visualiseur | ✅ | ✅ | ❌ | 🛑 |
| Transcription | ✅ | ❌ | ✅ | 🛑 |
| Nettoyage auto | ✅ | ✅ | ✅ | ✅ |
| Arrêt forcé | ❌ | ❌ | ❌ | ✅ |
| Recommandé | ⭐ | 🔧 | 🔧 | 🛑 |

---

## 🔧 Exemples d'utilisation

### Scénario 1 : Usage normal
```batch
REM Double-cliquer sur start.bat
start.bat
```
→ Tout démarre automatiquement !

### Scénario 2 : Test du visualiseur
```batch
REM Tester uniquement l'interface graphique
start_visualizer.bat
```
→ La fenêtre apparaît, vous pouvez la manipuler.

### Scénario 3 : Transcription sans visualiseur
```batch
REM Mode console pure
start_transcription.bat
```
→ Système actif, pas de fenêtre graphique.

### Scénario 4 : Arrêt forcé de toutes les instances
```batch
REM Si les processus ne répondent pas
stop_all.bat
```
→ Tout s'arrête immédiatement !

### Scénario 5 : Redémarrage propre
```batch
REM 1. Arrêter tout
stop_all.bat

REM 2. Attendre 2 secondes...

REM 3. Relancer
start.bat
```
→ Redémarrage propre du système.

---

## 🛠️ Dépannage

### Le script ne démarre pas
```powershell
# Vérifier que le venv existe
dir .venv\Scripts\python.exe
```

### Des instances restent bloquées
```batch
REM Forcer l'arrêt de tout
stop_all.bat
```

### PySide6 manquant
Les scripts installent automatiquement PySide6 s'il manque.
Si l'installation échoue :
```powershell
.venv\Scripts\python.exe -m pip install PySide6 PySide6-WebEngine
```

### Le visualiseur ne s'affiche pas
```batch
REM Lancer manuellement avec console pour voir les erreurs
.venv\Scripts\python.exe visualizer_window.py
```

### La transcription ne fonctionne pas
```batch
REM Vérifier les dépendances
.venv\Scripts\python.exe -m pip list
```

---

## 🎯 Recommandations

| Situation | Script à utiliser |
|-----------|-------------------|
| 💼 Travail quotidien | `start.bat` |
| 🧪 Test du visualiseur | `start_visualizer.bat` |
| 🔍 Debug transcription | `start_transcription.bat` |
| 🚀 Démo rapide | `start.bat` |
| 🎨 Modification CSS/JS | `start_visualizer.bat` |

---

## 📝 Notes

- **pythonw.exe** est utilisé pour le visualiseur (pas de console)
- **python.exe** est utilisé pour la transcription (console visible)
- Les scripts vérifient automatiquement les dépendances
- Le nettoyage automatique tue les processus pythonw.exe orphelins

---

## 🔗 Fichiers liés

- `visualizer_window.py` - Code de la fenêtre native
- `main_enhanced.py` - Application de transcription
- `shared_state.py` - État partagé entre les composants
- `VISUALIZER_NATIVE.md` - Documentation technique complète

---

**Astuce** : Créez des raccourcis sur le bureau pour un accès rapide !

```
Clic droit sur start.bat → Envoyer vers → Bureau (créer un raccourci)
```
