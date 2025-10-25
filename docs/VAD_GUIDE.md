# Guide de Détection Vocale Avancée (VAD)

## Vue d'ensemble

Le système de détection vocale avancée distingue la **voix humaine** du **bruit ambiant** en utilisant une combinaison de techniques :

1. **Silero VAD** - Modèle deep learning pré-entraîné (~1MB)
2. **Zero Crossing Rate (ZCR)** - Analyse du taux de passage par zéro
3. **RMS Energy** - Seuil d'énergie pour pré-filtrage rapide

## Architecture

```
Audio Input (sounddevice)
    │
    ├─► RMS Check (fast pre-filter)
    │   └─► < threshold → REJECT (pure silence)
    │
    ├─► Silero VAD (ML classifier)
    │   └─► Probability 0.0-1.0
    │       └─► < 0.5 → REJECT (noise/non-speech)
    │
    └─► ZCR Filter (optional)
        └─► Outside [0.02, 0.30] → REJECT (white noise/hum)
```

## Activation

### 1. Configuration

Éditez `core/config.py` :

```python
# Active la détection avancée voix/bruit
ENABLE_ADVANCED_VAD = True

# Seuil de probabilité Silero (0.0-1.0)
SILERO_THRESHOLD = 0.5  # 0.5 = équilibré (recommandé)

# Active le filtre ZCR
USE_ZCR_FILTER = True

# Mode debug (affiche les métriques en temps réel)
DEBUG_VAD = False
```

### 2. Test du système

Avant de lancer l'application complète :

```bash
.venv\Scripts\python.exe scripts\test_vad.py
```

Sortie attendue :
```
[OK] PyTorch version: 2.5.1+cu121
[OK] CUDA disponible: True
[OK] Silero VAD charge avec succes
[OK] VoiceDetector initialise
[SUCCESS] Systeme VAD fonctionnel!
```

### 3. Lancement normal

```bash
scripts\start_transcription.bat
```

## Réglage des paramètres

### Seuil Silero (`SILERO_THRESHOLD`)

| Valeur | Comportement | Usage |
|--------|--------------|-------|
| 0.3 | Très sensible | Détecte chuchotements, peut avoir faux positifs |
| **0.5** | **Équilibré** | **Recommandé - bon compromis voix/bruit** |
| 0.7 | Strict | Rejette plus de bruit, peut manquer parole faible |

### Plage ZCR

- **ZCR_MIN = 0.02** : En dessous = bourdonnement/DC offset
- **ZCR_MAX = 0.30** : Au-dessus = bruit blanc/sifflement

La voix humaine a typiquement un ZCR entre 0.05 et 0.25.

## Mode Debug

Activez `DEBUG_VAD = True` pour voir les métriques en temps réel :

```
[VAD] ✓ VOIX: RMS=0.045000, Silero=0.876, ZCR=0.1234
[VAD] Silero=0.123 < 0.5 → NOISE
[VAD] RMS=0.001200 < 0.003 → SILENCE
```

Utilisez ces informations pour ajuster :
- Si trop de **faux positifs** (bruit détecté comme voix) → augmentez `SILERO_THRESHOLD`
- Si **parole manquée** → baissez `SILERO_THRESHOLD` ou `ENERGY_THRESHOLD`

## Exemples de détection

### ✅ Voix humaine détectée

```
Audio : "Bonjour, comment ça va ?"
RMS   : 0.045
Silero: 0.876  ← Haute probabilité
ZCR   : 0.123  ← Dans la plage vocale
→ VOIX détectée
```

### ❌ Bruit blanc rejeté

```
Audio : Ventilateur, sifflement
RMS   : 0.052
Silero: 0.112  ← Faible probabilité
ZCR   : 0.456  ← Trop élevé (au-dessus de 0.30)
→ BRUIT rejeté
```

### ❌ Clavier/souris rejeté

```
Audio : Clics de clavier
RMS   : 0.023
Silero: 0.287  ← Probabilité moyenne-faible
ZCR   : 0.089
→ BRUIT rejeté (Silero < 0.5)
```

## Performance

- **Silero VAD** : ~1-2ms par chunk (512 samples) sur GPU
- **ZCR** : <0.1ms (calcul numpy simple)
- **Impact total** : Négligeable (<5ms par bloc audio)

### Configuration système

- **GPU recommandé** : NVIDIA avec CUDA (détection 10x plus rapide)
- **CPU acceptable** : Intel i5/Ryzen 5 ou supérieur
- **RAM** : +50MB pour le modèle Silero

## Dépendances

Le système VAD avancé nécessite PyTorch :

```bash
# CUDA 12.1 (GPU NVIDIA)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# CPU uniquement
pip install torch torchaudio
```

Silero VAD est téléchargé automatiquement (~1MB) au premier lancement.

## Désactivation

Pour revenir au mode RMS basique :

```python
# core/config.py
ENABLE_ADVANCED_VAD = False
```

Le système utilisera uniquement `ENERGY_THRESHOLD` (détection simple mais sensible au bruit).

## Intégration dans l'application

Le VoiceDetector est initialisé automatiquement dans `core/engine.py` :

```python
ctx.voice_detector = VoiceDetector(
    sample_rate=16000,
    silero_threshold=0.5,
    use_zcr_filter=True,
)
```

Utilisé dans `core/processor.py` via :

```python
if detect_activity(audio_block, ctx.voice_detector):
    # Voix détectée → traiter
    preview_buffer.append(audio_block)
```

## Troubleshooting

### PyTorch non installé

```
[ERROR] PyTorch non installe: No module named 'torch'
→ pip install torch torchaudio
```

### Silero VAD échoue

```
[ERROR] Echec chargement Silero VAD: ...
→ Vérifiez connexion internet (téléchargement initial)
→ Système bascule en mode RMS automatiquement
```

### Détection trop sensible

```
→ Augmentez SILERO_THRESHOLD (0.5 → 0.6 ou 0.7)
→ Vérifiez ENERGY_THRESHOLD (peut-être trop bas)
```

### Voix non détectée

```
→ Baissez SILERO_THRESHOLD (0.5 → 0.4 ou 0.3)
→ Activez DEBUG_VAD pour voir les probabilités réelles
```

## Fichiers modifiés

- `core/voice_detector.py` - Nouvelle classe VoiceDetector
- `core/config.py` - Configuration VAD
- `core/audio_capture.py` - Integration detect_activity()
- `core/engine.py` - Initialisation VoiceDetector
- `shared/context.py` - AppContext.voice_detector
- `scripts/test_vad.py` - Script de test

## Références

- [Silero VAD](https://github.com/snakers4/silero-vad) - Modèle officiel
- [PyTorch](https://pytorch.org/) - Framework ML
- [Zero Crossing Rate](https://en.wikipedia.org/wiki/Zero-crossing_rate) - Wikipédia
