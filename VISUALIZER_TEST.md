# Visualiseur Micro - Guide de Test

## ✅ Vérifications effectuées

### 1. **Syntaxe Python** ✓
- Compilation sans erreur : `python -m py_compile mic_visualizer.py`
- Imports PySide6 corrects
- Types et annotations corrects

### 2. **HTML/JavaScript** ✓
- Guillemets simples pour éviter les problèmes d'échappement
- Import ES Module correct : `import RecordPlugin from 'https://unpkg.com/wavesurfer.js@7/dist/plugins/record.esm.js'`
- Gestion d'erreurs avec logs de debug
- Vérification de chargement WaveSurfer et RecordPlugin

### 3. **Permissions Qt WebEngine** ✓
- `LocalContentCanAccessRemoteUrls` activé pour charger les CDN
- Permission microphone accordée via `MediaAudioCapture`
- Gestion des callbacks de permission

### 4. **Intégration avec main.py** ✓
- `start_visualizer()` : lance le processus en arrière-plan
- `stop_visualizer()` : ferme proprement le processus
- Flag `CREATE_NO_WINDOW` pour éviter une fenêtre console supplémentaire

## 🧪 Tests à effectuer

### Test 1 : HTML standalone
```bash
# Ouvrir test_visualizer.html dans un navigateur
# Vérifier :
# - Les boutons s'affichent
# - Le dropdown micro se remplit
# - La forme d'onde apparaît
# - L'enregistrement démarre
```

### Test 2 : Visualizer Python seul
```bash
python test_visualizer.py
# ou directement :
python mic_visualizer.py
```

**Vérifications** :
- ✓ Fenêtre s'ouvre (720x160)
- ✓ Toujours au-dessus (par défaut)
- ✓ Liste des micros se charge
- ✓ Forme d'onde animée
- ✓ Boutons Record/Pause fonctionnels
- ✓ Timer affiche le temps

**Raccourcis clavier** :
- `Espace` : Toggle record/stop
- `P` : Pause/Resume
- `T` : Toggle always-on-top
- `Esc` : Fermer

### Test 3 : Intégration main.py
```bash
python main.py
```

**Vérifications** :
- ✓ Visualizer se lance automatiquement
- ✓ Transcription Whisper fonctionne en parallèle
- ✓ Ctrl+C arrête tout proprement
- ✓ Visualizer se ferme avec le script

## 🔧 Dépendances requises

```bash
pip install --upgrade pip
pip install PySide6 sounddevice numpy
pip install faster-whisper keyboard pyperclip
```

## 🐛 Résolution de problèmes

### Problème : "WaveSurfer is not defined"
**Cause** : CDN non accessible ou bloqué
**Solution** : 
- Vérifier la connexion internet
- Essayer dans un navigateur : https://unpkg.com/wavesurfer.js@7
- Vérifier les logs dans la console Qt (F12 si DevTools activés)

### Problème : "Aucun micro détecté"
**Cause** : Permissions Windows ou micro non connecté
**Solution** :
- Paramètres Windows → Confidentialité → Microphone
- Autoriser les applications de bureau
- Vérifier que le micro est branché et activé

### Problème : Fenêtre noire / rien ne s'affiche
**Cause** : Script HTML ne charge pas
**Solution** :
- Vérifier les logs console Python
- Tester test_visualizer.html dans un navigateur
- Vérifier que PySide6 WebEngine est installé

### Problème : Forme d'onde ne bouge pas
**Cause** : Enregistrement pas démarré ou micro muet
**Solution** :
- Cliquer sur "Record" manuellement
- Vérifier le niveau micro dans Windows
- Tester avec test_visualizer.html pour isoler le problème

## 📝 Points clés de l'implémentation

1. **Module ES** : Utilisation de `<script type='module'>` pour import dynamique
2. **Async/Await** : Gestion asynchrone des permissions et devices
3. **Error handling** : Affichage des erreurs dans l'UI + console
4. **Debug logs** : Messages de debug pour tracer l'exécution
5. **Subprocess** : Visualizer lancé dans un processus séparé (évite les conflits Qt event loop)

## ✨ Fonctionnalités

- ✅ Enregistrement micro en temps réel
- ✅ Forme d'onde animée (continuous/scrolling)
- ✅ Sélection du périphérique audio
- ✅ Timer d'enregistrement
- ✅ Pause/Resume
- ✅ Sauvegarde des enregistrements (Download)
- ✅ Playback des enregistrements
- ✅ Always-on-top toggleable
- ✅ Raccourcis clavier
- ✅ Intégration transparente avec Whisper

## 🎯 Validation finale

Avant de dire que tout fonctionne :

1. ✅ `python -m py_compile mic_visualizer.py` → pas d'erreur
2. ⏳ Ouvrir `test_visualizer.html` → forme d'onde visible
3. ⏳ `python mic_visualizer.py` → fenêtre s'ouvre, recording démarre
4. ⏳ `python test_visualizer.py` → visualizer se lance et s'arrête proprement
5. ⏳ `python main.py` → visualizer + transcription fonctionnent ensemble

**Statut actuel** : Étapes 1 complète, tests 2-5 à effectuer par l'utilisateur.
