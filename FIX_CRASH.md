# Fix Python Crash au Démarrage

## Problèmes Identifiés

### 1. Dépendance Qt Manquante (CRITIQUE)

**Erreur:**
```
qt.qpa.plugin: From 6.5.0, xcb-cursor0 or libxcb-cursor0 is needed
Could not load the Qt platform plugin "xcb"
```

**Solution:**
```bash
sudo apt install libxcb-cursor0
```

OU utiliser le script automatique:
```bash
sudo bash scripts/fix_qt_deps.sh
```

### 2. Port 5432 Déjà Utilisé (CORRIGÉ)

**Erreur:**
```
Address already in use
Port 5432 is in use by another program
```

**Solution appliquée:**
- Le port a été changé de 5432 à 5433 dans `api/config.py`
- PostgreSQL utilise généralement le port 5432

## Procédure de Correction Complète

### Étape 1: Installer la dépendance Qt manquante

```bash
sudo apt install libxcb-cursor0
```

### Étape 2: Vérifier l'installation

```bash
dpkg -l | grep libxcb-cursor0
```

Vous devriez voir:
```
ii  libxcb-cursor0:amd64  0.1.x  ...
```

### Étape 3: Relancer l'application

```bash
./stop.sh          # Arrêter toute instance en cours
./start_debug.sh   # Relancer en mode debug
```

## Détails Techniques

### Changements Appliqués

**Fichiers modifiés:**
- `api/config.py` - Port changé de 5432 → 5433
- `scripts/install_system_deps.sh` - Ajout de libxcb-cursor0
- `scripts/fix_qt_deps.sh` - Nouveau script pour installer Qt deps

### Pourquoi Ce Problème Arrive

- **PySide6 >= 6.5.0** nécessite `libxcb-cursor0` pour le backend xcb (X11)
- Sans cette bibliothèque, Qt ne peut pas créer l'interface graphique
- Le port 5432 est le port par défaut de PostgreSQL

### Vérifications Supplémentaires

Si le problème persiste après l'installation:

1. **Vérifier l'environnement graphique:**
   ```bash
   echo $DISPLAY
   # Doit afficher quelque chose comme :0 ou :1
   ```

2. **Tester Qt directement:**
   ```bash
   .venv/bin/python -c "from PySide6.QtWidgets import QApplication; import sys; app = QApplication(sys.argv); print('Qt OK')"
   ```

3. **Vérifier les plugins Qt disponibles:**
   ```bash
   .venv/bin/python -c "from PySide6.QtGui import QGuiApplication; print(QGuiApplication.platformName())"
   ```

## Résumé des Commandes

```bash
# Installation de la dépendance
sudo apt install libxcb-cursor0

# Test et lancement
./stop.sh
./start_debug.sh
```

Une fois l'application lancée avec succès, vous verrez:
- Le visualiseur Qt6 s'ouvrir
- Les logs de démarrage dans le terminal
- L'icône du system tray apparaître

## Besoin d'Aide ?

Si le problème persiste après avoir installé `libxcb-cursor0`:
1. Vérifiez les logs: `tail -f /tmp/transcription_*.log`
2. Lancez en mode debug: `./start_debug.sh`
3. Partagez le message d'erreur complet
