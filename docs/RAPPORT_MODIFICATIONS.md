# Rapport des Modifications - Micro Transcription

Date: 2025-12-06

## Résumé

Ce document récapitule toutes les modifications apportées pour résoudre les problèmes de transcription et de collage, ainsi que les optimisations de configuration.

---

## Fonctionnalités Désactivées (temporairement)

### 1. Silero VAD - DÉSACTIVÉ
**Fichier:** `core/config.py`
```python
ENABLE_ADVANCED_VAD = False
```
**Raison:** Silero retournait des probabilités très faibles (0.01-0.1) même avec une voix normale, empêchant la détection de parole.
**Alternative:** Utilisation du mode RMS legacy (détection basique par énergie sonore).

### 2. Réduction de bruit (noisereduce) - DÉSACTIVÉ
**Fichier:** `core/config.py`
```python
ENABLE_NOISE_REDUCTION = False
```
**Raison:** Bug d'allocation mémoire - noisereduce tentait d'allouer 68 GB de RAM pour un array de shape (152000, 60001).
**Impact:** La transcription fonctionne sans réduction de bruit préalable.

### 3. Filtre VAD Whisper - DÉSACTIVÉ
**Fichier:** `core/config.py`
```python
VAD_FILTER = False
```
**Raison:** Le filtre VAD interne de Whisper rejetait des segments audio valides comme "silence", empêchant la transcription.
**Note:** Peut être réactivé si les problèmes de détection sont résolus.

---

## Fonctionnalités Activées

### 1. Mode Debug Audio
**Fichier:** `core/config.py`
```python
DEBUG_AUDIO_LEVEL = True
```
**Effet:** Affiche les niveaux RMS en temps réel pour diagnostic.

### 2. Debug Whisper
**Fichier:** `core/models.py`
**Effet:** Logs détaillés de la transcription (durée audio, RMS, nombre de segments, résultat).

---

## Paramètres Modifiés

### Configuration Audio

| Paramètre | Ancienne valeur | Nouvelle valeur | Raison |
|-----------|-----------------|-----------------|--------|
| `SILENCE_BLOCKS_BEFORE_FLUSH` | 2 | 5 | Évite les flush prématurés sur pauses courtes |
| `ENERGY_THRESHOLD` | 0.015 | 0.008 | Plus sensible pour détecter la parole normale |
| `SILERO_THRESHOLD` | 0.5 | 0.15 | Réduit car micro renvoie des probabilités faibles |
| `ADAPTIVE_BOOST_FACTOR` | 1.5 | 1.2 | Plus sensible pour micros faibles |

### Configuration Whisper/GPU

| Paramètre | Ancienne valeur | Nouvelle valeur | Raison |
|-----------|-----------------|-----------------|--------|
| `WHISPER_MODEL` | "small" | "large" | Meilleure qualité de transcription |
| `DEVICE` | "cpu" | "cuda" | GPU NVIDIA RTX 4060 (8 GB VRAM) |
| `FLOAT_PRECISION` | "float32" | "float16" | Optimisé pour GPU (2x plus rapide) |

**GPU Actif:** NVIDIA GeForce RTX 4060 Laptop GPU (8 GB VRAM)
- Driver: NVIDIA 580.95.05
- CUDA: 13.0 / PyTorch CUDA: 12.1
- Le modèle large tourne maintenant sur GPU pour une transcription rapide et précise

---

## Corrections de Code

### 1. Collage sous Wayland/XWayland
**Fichier:** `core/audio_capture.py`

**Problème:** Le collage via xdotool ne fonctionnait pas sous Wayland.

**Solution:**
- Détection XWayland (DISPLAY défini même sous Wayland)
- Utilisation explicite de `DISPLAY=:0` dans l'environnement
- Ajout d'un délai de stabilisation du focus (50ms)
- Timeout augmenté à 10s
- Meilleure gestion des erreurs avec logs

```python
def _detect_linux_environment() -> tuple[str, bool, bool]:
    # Retourne maintenant aussi xwayland_available
    xwayland_available = has_display and xdotool_available
```

### 2. Fenêtre toujours au premier plan
**Fichier:** `ui/visualizer_app.py`

**Amélioration:**
- Ajout du flag `Qt.WindowType.Tool` pour meilleur comportement sous Wayland
- Appel forcé de `raise_()` et `activateWindow()` après application des flags

---

## Architecture - État Actuel

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUX DE TRANSCRIPTION                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Microphone → Capture Audio → Détection RMS → Buffer        │
│                    ↓                                        │
│              [Silero VAD]  ← DÉSACTIVÉ                      │
│                    ↓                                        │
│              [Noise Reduce] ← DÉSACTIVÉ                     │
│                    ↓                                        │
│              Whisper Large (CUDA)                           │
│                    ↓                                        │
│              xdotool (XWayland) → Collage texte             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Tests Recommandés

1. **Vérifier GPU disponible:**
   ```bash
   nvidia-smi
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Tester xdotool:**
   ```bash
   DISPLAY=:0 xdotool type "test"
   ```

3. **Lancer l'application:**
   ```bash
   .venv/bin/python main.py
   ```

---

## Problèmes Connus

1. **Silero VAD peu fiable** - Les probabilités retournées sont très faibles même avec une voix claire. Nécessite investigation sur le format audio envoyé au modèle.

2. **noisereduce crash mémoire** - Bug dans la bibliothèque noisereduce qui tente d'allouer une matrice énorme. Peut nécessiter une mise à jour ou un patch.

3. **Hotkeys sous Wayland** - pynput peut avoir des limitations sous Wayland pur. Fonctionne via XWayland.

---

## Fichiers Modifiés

- `core/config.py` - Paramètres de configuration
- `core/models.py` - Debug Whisper
- `core/audio_capture.py` - Logique de collage XWayland
- `ui/visualizer_app.py` - Fenêtre toujours au premier plan

---

## Prochaines Étapes

1. [ ] Investiguer pourquoi Silero VAD retourne des probabilités faibles
2. [ ] Corriger le bug noisereduce ou trouver une alternative
3. [ ] Tester les hotkeys F8/F9 sous Wayland pur
4. [ ] Optimiser les paramètres pour réduire les faux positifs/négatifs
