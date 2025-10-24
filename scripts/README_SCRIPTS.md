# Scripts de Gestion du Système de Transcription

## 📋 Vue d'ensemble

Ce dossier contient les scripts batch pour démarrer, arrêter et gérer le système de transcription audio.

## 🚀 Scripts Disponibles

### 1. `start_transcription.bat`
**Démarrage en mode normal (arrière-plan)**
- Lance le système complet en arrière-plan
- Aucune console visible
- Les logs sont désactivés pour les performances
- Utilise `pythonw.exe` (mode silencieux)

**Utilisation :**
```batch
scripts\start_transcription.bat
```

### 2. `start_transcription_debug.bat`
**Démarrage en mode DEBUG**
- Lance le système avec console visible
- Affiche tous les logs en temps réel
- Idéal pour diagnostiquer les problèmes
- Utilise `python.exe` (mode console)

**Utilisation :**
```batch
scripts\start_transcription_debug.bat
```

### 3. `stop_transcription.bat`
**Arrêt du système**
- Arrête tous les modules (Core, UI, API)
- Ciblage précis des processus Python du projet
- **Protection intégrée :** ne tue PAS le processus batch appelant
- Vérification finale des processus restants

**Utilisation :**
```batch
scripts\stop_transcription.bat
```

## 🛡️ Protection Contre l'Auto-Destruction

### Problème Résolu
Les scripts précédents pouvaient se tuer eux-mêmes lors de l'arrêt des processus Python.

### Solution Implémentée

#### Dans `stop_transcription.bat`
- ✅ Utilise `wmic` pour cibler **précisément** les processus Python
- ✅ Filtre par ligne de commande (`main.py`, `ui.visualizer`, `api.server`)
- ✅ **NE TUE PAS** les processus `cmd.exe` ou batch scripts
- ✅ Affiche les PIDs des processus arrêtés pour transparence

#### Dans `start_transcription.bat` et `start_transcription_debug.bat`
- ✅ Augmentation du délai après `stop_transcription.bat` (1s → 2s)
- ✅ Messages informatifs lors de l'appel au script d'arrêt
- ✅ Les scripts se terminent normalement après le démarrage

## 🔍 Détails Techniques

### Ciblage des Processus

Le script `stop_transcription.bat` utilise maintenant :

```batch
wmic process where "name='python.exe' and CommandLine like '%main.py%'" get ProcessId
```

Au lieu de :
```batch
taskkill /F /FI "COMMANDLINE eq *main.py*"
```

**Avantages :**
- Pas de wildcard sur le nom du processus
- Filtrage précis sur la ligne de commande Python
- Les scripts batch sont ignorés automatiquement

### Variables d'Environnement

Le script utilise `EnableDelayedExpansion` pour :
- Gérer les PIDs dynamiquement dans les boucles
- Éviter les conflits de variables
- Améliorer la robustesse

## 📊 Processus Ciblés

| Module | Processus | Ligne de Commande Recherchée |
|--------|-----------|------------------------------|
| **CORE** | `python.exe` / `pythonw.exe` | `*main.py*` |
| **UI** | `python.exe` / `pythonw.exe` | `*ui.visualizer_app*` ou `*-m ui*` |
| **API** | `python.exe` / `pythonw.exe` | `*api.server*` |

## 🔧 Dépannage

### Le script crash toujours ?

1. **Vérifiez les permissions**
   ```batch
   # Exécuter en tant qu'administrateur si nécessaire
   ```

2. **Vérifiez que wmic fonctionne**
   ```batch
   wmic process get ProcessId,CommandLine
   ```

3. **Testez manuellement le ciblage**
   ```batch
   wmic process where "name='python.exe' and CommandLine like '%main.py%'" get ProcessId
   ```

### Le système ne démarre pas ?

1. Lancez en mode DEBUG :
   ```batch
   scripts\start_transcription_debug.bat
   ```

2. Vérifiez les étapes affichées :
   - ✅ Arrêt instances précédentes
   - ✅ Vérification environnement
   - ✅ Vérification dépendances
   - ✅ Vérification structure
   - ✅ Démarrage modules

### Les processus ne s'arrêtent pas ?

1. Lancez `stop_transcription.bat` directement
2. Vérifiez les messages `[INFO] Arret processus ... PID: ...`
3. Si aucun PID n'est affiché, les processus n'existent pas

## 📝 Notes Importantes

- ⚠️ Les scripts doivent être exécutés depuis `scripts\` ou avec leur chemin complet
- ⚠️ Le virtual environment `.venv` doit exister à la racine du projet
- ⚠️ Les modules `core/`, `ui/`, `api/` doivent exister
- ✅ Les scripts s'adaptent automatiquement au répertoire d'exécution

## 🎯 Ordre d'Exécution Recommandé

1. **Première utilisation :**
   ```batch
   scripts\start_transcription_debug.bat
   # Vérifier que tout fonctionne
   # Ctrl+C pour arrêter
   ```

2. **Utilisation normale :**
   ```batch
   scripts\start_transcription.bat
   # Le système démarre en arrière-plan
   ```

3. **Arrêt :**
   ```batch
   scripts\stop_transcription.bat
   # Arrête tous les modules proprement
   ```

## 🔄 Changements Récents (Oct 2025)

### v2.1 - Protection Anti-Crash
- ✅ Utilisation de `wmic` au lieu de `taskkill` avec wildcards
- ✅ Ciblage précis des processus Python par ligne de commande
- ✅ Protection des scripts batch appelants
- ✅ Augmentation des délais de sécurité
- ✅ Messages informatifs avec PIDs
- ✅ Variable `EnableDelayedExpansion` pour robustesse

---

**Auteur :** Système de Transcription Audio v2.0  
**Dernière mise à jour :** Octobre 2025
