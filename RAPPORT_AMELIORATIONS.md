# Rapport d'Analyse et Améliorations du Système de Transcription

> **Objectif :** Améliorer la détection vocale robuste (distinguer la parole du bruit TV, aspirateur, etc.) et maximiser la qualité de transcription.

---

## STATUT D'IMPLÉMENTATION

| Amélioration | Statut | Fichier(s) |
|--------------|--------|------------|
| Silero VAD activé | FAIT | `core/config.py` |
| Vote par fenêtre glissante | FAIT | `core/voice_detector.py` |
| Recalibration automatique | FAIT | `core/voice_detector.py` |
| Réduction de bruit (noisereduce) | FAIT | `core/noise_reduction.py` |
| Intégration dans preprocessing | FAIT | `core/audio_preprocessing.py` |
| Détection fin de phrase | FAIT | `core/phrase_detector.py` |
| Limite buffer production | FAIT | `core/config.py`, `core/processor.py` |
| Prompt initial Whisper | FAIT | `core/config.py`, `core/models.py` |
| Détecteur de locuteur | FAIT | `core/speaker_detector.py` |
| Export configurations | FAIT | `shared/config.py` |

---

## Table des Matières

1. [Résumé Exécutif](#1-résumé-exécutif)
2. [Architecture Actuelle](#2-architecture-actuelle)
3. [Problèmes Identifiés](#3-problèmes-identifiés)
4. [Améliorations Prioritaires](#4-améliorations-prioritaires)
5. [Améliorations Avancées](#5-améliorations-avancées)
6. [Plan d'Implémentation](#6-plan-dimplémentation)

---

## 1. Résumé Exécutif

### Points Forts Actuels
- Architecture modulaire bien structurée
- Support GPU CUDA avec faster-whisper
- Système de veille intelligent (économie ressources)
- Pipeline de prétraitement audio existant

### Faiblesses Critiques
| Problème | Impact | Priorité |
|----------|--------|----------|
| VAD avancée désactivée | Impossible de distinguer voix/bruit | **CRITIQUE** |
| Seuil RMS statique | Faux positifs avec bruit ambiant | **HAUTE** |
| Pas de réduction de bruit | Transcription polluée | **HAUTE** |
| Buffer illimité | Risque mémoire | **MOYENNE** |
| Pas de détection de fin de phrase | Latence élevée | **MOYENNE** |

---

## 2. Architecture Actuelle

### Pipeline Audio Actuel

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CAPTURE AUDIO                                │
│  sounddevice → 16kHz mono → blocks 0.5s (8000 samples)              │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VAD (VOICE ACTIVITY DETECTION)                    │
│  Mode actuel: RMS > 0.015 (seuil statique)                          │
│  Mode avancé: DÉSACTIVÉ (Silero VAD + ZCR)                          │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        PRÉTRAITEMENT                                 │
│  1. Filtre passe-haut 80Hz (supprime bourdonnement)                 │
│  2. Amplification (target RMS 0.1, max gain 2x)                     │
│  3. Normalisation [-1, 1]                                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       TRANSCRIPTION WHISPER                          │
│  Modèle: large (2.9GB) sur CUDA                                     │
│  Déclencheur: 1.0s de silence (2 blocks × 0.5s)                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Fichiers Clés Analysés

| Fichier | Lignes | Rôle |
|---------|--------|------|
| `core/config.py` | 185 | Configuration centralisée |
| `core/processor.py` | 168 | Boucle principale audio |
| `core/audio_capture.py` | 264 | Callback audio + VAD legacy |
| `core/voice_detector.py` | 389 | VAD avancée (désactivée) |
| `core/audio_preprocessing.py` | 118 | Filtrage audio |
| `core/models.py` | 184 | Chargement/transcription Whisper |

---

## 3. Problèmes Identifiés

### 3.1 VAD Primitive (CRITIQUE)

**Localisation :** `core/audio_capture.py:71-99`

**Code actuel :**
```python
# Mode legacy: simple RMS threshold
rms = float(np.sqrt(np.mean(np.square(audio_block), dtype=np.float64)))
return rms > config.ENERGY_THRESHOLD  # 0.015
```

**Problème :**
- Un simple seuil d'énergie ne distingue PAS la voix du bruit
- Un aspirateur (bruit fort) → faux positif → transcription de "bruit"
- Une TV en fond (dialogue) → faux positif → transcription de la TV
- Seuil statique inadapté aux environnements variables

**Impact :**
- Transcription polluée par le bruit ambiant
- Pas de distinction entre votre voix et celle de la TV
- Système ne sait pas quand vous parlez réellement

---

### 3.2 VAD Avancée Désactivée

**Localisation :** `core/config.py:49`

```python
ENABLE_ADVANCED_VAD = False  # NOTE: Désactivé car nécessite torch
```

**Problème :**
Le système possède déjà un excellent détecteur de voix (`VoiceDetector`) combinant :
1. **Silero VAD** : Réseau de neurones spécialisé dans la détection vocale
2. **Zero Crossing Rate** : Distingue bruit blanc vs voix humaine
3. **Détection adaptative** : Compare le niveau actuel au bruit ambiant

Mais il est **désactivé** car PyTorch n'est pas dans les dépendances.

**Solution :** Activer `ENABLE_ADVANCED_VAD = True` après installation de torch.

---

### 3.3 Absence de Réduction de Bruit

**Localisation :** `core/audio_preprocessing.py`

**État actuel :**
```python
def preprocess_audio(audio, sample_rate=16000):
    audio = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)  # Seul filtre
    audio = amplify_audio(audio, target_rms=0.1)
    audio = normalize_audio(audio)
    return audio
```

**Problème :**
- Le filtre passe-haut 80Hz ne supprime que le bourdonnement électrique
- Aucune suppression du bruit large bande (aspirateur, ventilateur, climatisation)
- Aucune suppression des fréquences non-vocales

**Bruits non traités :**
| Type de Bruit | Fréquences | Traitement Actuel |
|---------------|------------|-------------------|
| Bourdonnement 50/60Hz | 50-60 Hz | ✅ Filtré (passe-haut 80Hz) |
| Aspirateur | 200-4000 Hz | ❌ Non traité |
| Ventilateur | 100-1000 Hz | ❌ Non traité |
| TV en fond | 100-8000 Hz | ❌ Non traité |
| Climatisation | 150-2000 Hz | ❌ Non traité |

---

### 3.4 Détection de Fin de Phrase Basique

**Localisation :** `core/config.py:38` et `core/processor.py:142`

```python
SILENCE_BLOCKS_BEFORE_FLUSH = 2  # 2 × 0.5s = 1.0s de silence
```

**Problème :**
- Attendre 1 seconde de silence complet est trop rigide
- Une pause naturelle dans une phrase peut déclencher la transcription
- Pas de détection de ponctuation ou de fin de phrase sémantique

**Impact :**
- Phrases coupées en plein milieu
- Transcription fragmentée

---

### 3.5 Absence de Contexte Phonétique

**Localisation :** `core/models.py:146-156`

```python
params = {
    "condition_on_previous_text": config.CONDITION_ON_PREVIOUS,  # True
    # Mais aucun contexte initial fourni
}
```

**Problème :**
- `condition_on_previous_text` est activé mais aucun prompt initial n'est fourni
- Whisper démarre sans contexte → peut mal interpréter les premiers mots
- Pas de vocabulaire spécialisé (noms propres, termes techniques)

---

### 3.6 Buffer Production Illimité

**Localisation :** `core/processor.py:67-68`

```python
preview_buffer: list[np.ndarray] = []
production_buffer: list[np.ndarray] = []  # Pas de limite !
```

**Problème :**
- Si vous parlez pendant 10 minutes sans pause, le buffer accumule ~19MB de données
- Risque de saturation mémoire
- Transcription d'un très long segment = latence énorme

**Calcul :**
```
10 min × 60 s × 16000 Hz × 4 bytes/sample = 38.4 MB
```

---

### 3.7 Prétraitement Identique Preview/Production

**Localisation :** `core/processor.py:125,145`

```python
preview_audio = preprocess_audio(preview_audio, sample_rate=config.SAMPLE_RATE)
production_audio = preprocess_audio(production_audio, sample_rate=config.SAMPLE_RATE)
# Même traitement pour les deux
```

**Problème :**
- Preview (temps réel) devrait être plus léger
- Production (qualité finale) devrait avoir un traitement plus poussé

---

### 3.8 Silero VAD : Taille de Fenêtre Sous-Optimale

**Localisation :** `core/voice_detector.py:205-232`

```python
required_samples = 512 if self.sample_rate == 16000 else 256

if len(audio) > required_samples:
    # Découpe en fenêtres de 512 samples
    # Retourne le MAXIMUM des probabilités
```

**Problème :**
- Fenêtres de 512 samples = 32ms à 16kHz
- Block audio = 8000 samples = 500ms
- Donc 15 fenêtres analysées mais seul le MAX est gardé
- Un pic de bruit peut donner un faux positif

**Amélioration :** Utiliser une moyenne pondérée ou un vote majoritaire.

---

### 3.9 Calibration Trop Courte

**Localisation :** `core/voice_detector.py:82-83`

```python
self._max_calibration_count: int = 4  # 4 chunks × 0.5s = 2 secondes
```

**Problème :**
- 2 secondes de calibration sont insuffisantes pour capturer le bruit ambiant réel
- Si vous parlez pendant la calibration, le niveau de référence sera faussé
- Pas de recalibration automatique

---

### 3.10 Pas de Distinction Voix Utilisateur vs Autres Voix

**Problème Conceptuel :**
Le système actuel détecte "une voix humaine" mais pas "VOTRE voix".

Si une TV diffuse un dialogue :
1. Silero VAD → détecte voix humaine ✓
2. ZCR → dans la plage vocale ✓
3. Boost factor → si TV forte → transcrit la TV ❌

**Solutions Potentielles :**
- Détection de direction (beamforming avec micro stéréo)
- Enregistrement d'empreinte vocale (speaker embedding)
- Détection de distance (voix proche vs lointaine)

---

## 4. Améliorations Prioritaires

### 4.1 PRIORITÉ CRITIQUE : Activer Silero VAD

**Action :** Installer les dépendances et activer le VAD avancé.

**Fichier :** `core/config.py:49`

```python
# AVANT
ENABLE_ADVANCED_VAD = False

# APRÈS
ENABLE_ADVANCED_VAD = True
```

**Dépendances à ajouter :**
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Impact attendu :**
- Réduction de 80% des faux positifs
- Distinction voix humaine vs bruit mécanique (aspirateur)
- Détection adaptative au bruit ambiant

---

### 4.2 PRIORITÉ HAUTE : Ajouter Réduction de Bruit Spectrale

**Nouveau fichier :** `core/noise_reduction.py`

**Algorithme recommandé :** Spectral Subtraction

```python
def spectral_subtraction(audio, sample_rate=16000, noise_frames=10):
    """
    Réduction de bruit par soustraction spectrale.

    1. Estime le spectre du bruit (premiers frames)
    2. Soustrait ce spectre du signal
    3. Préserve les harmoniques de la voix
    """
    import numpy as np
    from scipy.signal import stft, istft

    # STFT
    f, t, Zxx = stft(audio, fs=sample_rate, nperseg=512, noverlap=384)

    # Estimation du bruit (moyenne des premiers frames)
    noise_spectrum = np.mean(np.abs(Zxx[:, :noise_frames]), axis=1, keepdims=True)

    # Soustraction spectrale avec floor (évite valeurs négatives)
    magnitude = np.maximum(np.abs(Zxx) - noise_spectrum * 1.5, 0.1 * np.abs(Zxx))
    phase = np.angle(Zxx)

    # Reconstruction
    Zxx_clean = magnitude * np.exp(1j * phase)
    _, audio_clean = istft(Zxx_clean, fs=sample_rate, nperseg=512, noverlap=384)

    return audio_clean.astype(np.float32)
```

**Intégration dans le pipeline :**
```python
# core/audio_preprocessing.py
def preprocess_audio(audio, sample_rate=16000, noise_profile=None):
    audio = apply_highpass_filter(audio, sample_rate, cutoff_hz=80.0)

    # NOUVEAU : Réduction de bruit spectrale
    if noise_profile is not None:
        audio = spectral_subtraction(audio, sample_rate, noise_profile)

    audio = amplify_audio(audio, target_rms=0.1)
    audio = normalize_audio(audio)
    return audio
```

---

### 4.3 PRIORITÉ HAUTE : Améliorer la Détection de Fin de Phrase

**Concept :** Combiner silence ET analyse prosodique.

**Nouveau fichier :** `core/phrase_detector.py`

```python
class PhraseEndDetector:
    """
    Détecte la fin de phrase en combinant :
    1. Silence (pause vocale)
    2. Chute d'énergie (fin de mot)
    3. Chute de pitch (intonation descendante = fin de phrase)
    """

    def __init__(self):
        self.energy_history = []
        self.pitch_history = []

    def is_phrase_end(self, audio_block, is_silent: bool) -> bool:
        energy = np.sqrt(np.mean(audio_block ** 2))
        self.energy_history.append(energy)

        # Fenêtre glissante de 5 blocs
        if len(self.energy_history) > 5:
            self.energy_history.pop(0)

        # Conditions de fin de phrase
        conditions = {
            "silence": is_silent,
            "energy_drop": self._detect_energy_drop(),
            "pitch_drop": self._detect_pitch_drop(audio_block),
        }

        # Fin de phrase si silence + au moins un autre indicateur
        return conditions["silence"] and (
            conditions["energy_drop"] or conditions["pitch_drop"]
        )

    def _detect_energy_drop(self) -> bool:
        if len(self.energy_history) < 3:
            return False
        recent = np.mean(self.energy_history[-2:])
        older = np.mean(self.energy_history[:-2])
        return recent < older * 0.3  # Chute de 70%

    def _detect_pitch_drop(self, audio) -> bool:
        # Simplification : utiliser autocorrélation pour détecter chute de F0
        # Implémentation complète nécessiterait librosa ou parselmouth
        return False  # TODO: Implémenter
```

---

### 4.4 PRIORITÉ HAUTE : Limiter le Buffer Production

**Fichier :** `core/config.py`

```python
# NOUVEAU
MAX_PRODUCTION_SECONDS = 30.0  # Forcer transcription après 30s
MAX_PRODUCTION_BLOCKS = int(MAX_PRODUCTION_SECONDS / BLOCK_SECONDS)  # 60 blocks
```

**Fichier :** `core/processor.py`

```python
# Ajouter dans la boucle principale
if len(production_buffer) >= config.MAX_PRODUCTION_BLOCKS:
    # Forcer la transcription même sans silence
    production_audio = np.concatenate(production_buffer, axis=0)
    production_audio = preprocess_audio(production_audio)
    final_text = transcribe_production(ctx, production_audio)
    if final_text:
        paste_via_clipboard(ctx, final_text)
    production_buffer.clear()
```

---

### 4.5 PRIORITÉ MOYENNE : Ajouter un Prompt Initial à Whisper

**Fichier :** `core/config.py`

```python
# NOUVEAU : Prompt initial pour guider Whisper
INITIAL_PROMPT = """
Ce texte est une transcription de dictée vocale en français.
Le locuteur parle clairement et distinctement.
"""

# Vocabulaire personnalisé (noms propres, termes techniques)
VOCABULARY_BOOST = [
    "Claude",
    "Anthropic",
    "Python",
    # Ajouter vos termes fréquents
]
```

**Fichier :** `core/models.py`

```python
def _run_transcription(model: WhisperModel, audio: np.ndarray) -> Optional[str]:
    params = {
        "language": config.LANGUAGE,
        "temperature": config.TEMPERATURE,
        "beam_size": config.BEAM_SIZE,
        "vad_filter": config.VAD_FILTER,
        "condition_on_previous_text": config.CONDITION_ON_PREVIOUS,
        "word_timestamps": config.WORD_TIMESTAMPS,
        "best_of": config.BEST_OF,
        # NOUVEAU
        "initial_prompt": config.INITIAL_PROMPT,
    }
    # ...
```

---

## 5. Améliorations Avancées

### 5.1 Distinction Voix Utilisateur vs TV (Speaker Diarization)

**Concept :** Créer une empreinte vocale de l'utilisateur et ne transcrire que cette voix.

**Implémentation avec pyannote.audio :**

```python
# core/speaker_detector.py
from pyannote.audio import Model
from pyannote.audio.pipelines import SpeakerDiarization
import torch

class SpeakerVerifier:
    """Vérifie si l'audio provient de l'utilisateur enregistré."""

    def __init__(self):
        self.model = Model.from_pretrained("pyannote/embedding")
        self.user_embedding = None

    def enroll_user(self, audio_samples: list[np.ndarray]):
        """Enregistre l'empreinte vocale de l'utilisateur."""
        embeddings = []
        for audio in audio_samples:
            emb = self.model(torch.from_numpy(audio))
            embeddings.append(emb)
        self.user_embedding = torch.mean(torch.stack(embeddings), dim=0)

    def is_user_speaking(self, audio: np.ndarray, threshold=0.7) -> bool:
        """Vérifie si l'audio correspond à l'utilisateur."""
        if self.user_embedding is None:
            return True  # Pas d'empreinte = accepte tout

        current_embedding = self.model(torch.from_numpy(audio))
        similarity = torch.cosine_similarity(
            current_embedding, self.user_embedding, dim=0
        )
        return similarity.item() > threshold
```

**Workflow :**
1. Au premier lancement : demander à l'utilisateur de lire 3 phrases
2. Calculer l'empreinte vocale moyenne
3. À chaque détection vocale : vérifier la similarité
4. Ne transcrire que si similarité > 70%

---

### 5.2 Réduction de Bruit par Deep Learning (RNNoise)

**Alternative à la soustraction spectrale :** Utiliser RNNoise (réseau de neurones pré-entraîné).

```bash
pip install noisereduce
```

```python
# core/noise_reduction.py
import noisereduce as nr

def denoise_audio(audio: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """
    Réduction de bruit par deep learning.
    Excellente suppression de bruit sans artefacts.
    """
    return nr.reduce_noise(
        y=audio,
        sr=sample_rate,
        stationary=False,  # Bruit non-stationnaire (aspirateur variable)
        prop_decrease=0.8,  # Réduction de 80%
    )
```

**Avantages :**
- Meilleure qualité que soustraction spectrale
- Préserve mieux la voix
- Gère les bruits non-stationnaires

**Inconvénients :**
- Plus lent (GPU recommandé)
- Dépendance supplémentaire

---

### 5.3 Détection de Distance (Voix Proche vs Lointaine)

**Concept :** Une voix proche a plus de basses fréquences (effet de proximité).

```python
def estimate_distance(audio: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Estime si la voix est proche (<50cm) ou lointaine (>1m).
    Basé sur le ratio basses/hautes fréquences.
    """
    from scipy.signal import butter, filtfilt

    # Filtre passe-bas (< 300 Hz)
    b_low, a_low = butter(4, 300 / (sample_rate / 2), btype='low')
    low_energy = np.mean(filtfilt(b_low, a_low, audio) ** 2)

    # Filtre passe-haut (> 2000 Hz)
    b_high, a_high = butter(4, 2000 / (sample_rate / 2), btype='high')
    high_energy = np.mean(filtfilt(b_high, a_high, audio) ** 2)

    ratio = low_energy / (high_energy + 1e-10)

    if ratio > 5.0:
        return "proche"  # < 50cm
    elif ratio > 2.0:
        return "medium"  # 50cm - 1m
    else:
        return "lointaine"  # > 1m
```

**Usage :** Ne transcrire que les voix "proches" pour ignorer la TV.

---

### 5.4 VAD avec Fenêtre Glissante et Vote

**Amélioration de `VoiceDetector.is_human_speech()` :**

```python
def _get_silero_probability_voting(self, audio: np.ndarray) -> float:
    """
    Analyse avec fenêtre glissante et vote majoritaire.
    Plus robuste qu'un simple MAX.
    """
    required_samples = 512
    hop_size = 256  # 50% overlap

    if len(audio) < required_samples:
        audio = np.pad(audio, (0, required_samples - len(audio)))
        return self._model(torch.from_numpy(audio).float(), self.sample_rate).item()

    votes = []
    for start in range(0, len(audio) - required_samples + 1, hop_size):
        chunk = audio[start:start + required_samples]
        prob = self._model(torch.from_numpy(chunk).float(), self.sample_rate).item()
        votes.append(prob > self.silero_threshold)

    # Vote majoritaire : >50% des fenêtres doivent détecter de la voix
    return sum(votes) / len(votes) > 0.5
```

---

### 5.5 Recalibration Automatique du Bruit Ambiant

**Amélioration de `VoiceDetector` :**

```python
def _auto_recalibrate(self) -> None:
    """
    Recalibre automatiquement le niveau de bruit ambiant.
    Appelé après 30 secondes d'inactivité.
    """
    if self._seconds_since_last_speech > 30:
        # Réinitialiser la calibration
        self._is_calibrating = True
        self._calibration_count = 0
        self._rms_history.clear()
        print("🔄 Recalibration du bruit ambiant...")
```

---

## 6. Plan d'Implémentation

### Phase 1 : Corrections Critiques (1-2 heures)

| Étape | Action | Fichier |
|-------|--------|---------|
| 1.1 | Installer PyTorch | `pip install torch` |
| 1.2 | Activer `ENABLE_ADVANCED_VAD = True` | `core/config.py:49` |
| 1.3 | Ajouter limite buffer production | `core/config.py` + `core/processor.py` |
| 1.4 | Ajouter prompt initial Whisper | `core/config.py` + `core/models.py` |

### Phase 2 : Réduction de Bruit (2-3 heures)

| Étape | Action | Fichier |
|-------|--------|---------|
| 2.1 | Créer `noise_reduction.py` | `core/noise_reduction.py` |
| 2.2 | Intégrer dans `preprocess_audio()` | `core/audio_preprocessing.py` |
| 2.3 | Ajouter noisereduce comme dépendance | `requirements.txt` |
| 2.4 | Tester avec différents bruits | - |

### Phase 3 : Détection Améliorée (3-4 heures)

| Étape | Action | Fichier |
|-------|--------|---------|
| 3.1 | Créer `phrase_detector.py` | `core/phrase_detector.py` |
| 3.2 | Intégrer dans processor.py | `core/processor.py` |
| 3.3 | Améliorer vote Silero VAD | `core/voice_detector.py` |
| 3.4 | Ajouter recalibration auto | `core/voice_detector.py` |

### Phase 4 : Distinction Utilisateur/TV (4-6 heures)

| Étape | Action | Fichier |
|-------|--------|---------|
| 4.1 | Créer `speaker_detector.py` | `core/speaker_detector.py` |
| 4.2 | Ajouter workflow d'enregistrement | `core/engine.py` |
| 4.3 | Intégrer vérification dans pipeline | `core/processor.py` |
| 4.4 | Ajouter UI pour enregistrement | `ui/` |

---

## Annexes

### A. Paramètres Recommandés pour Environnement Bruyant

```python
# core/config.py

# VAD
ENABLE_ADVANCED_VAD = True
SILERO_THRESHOLD = 0.6  # Plus strict
USE_ZCR_FILTER = True
USE_ADAPTIVE_DETECTION = True
ADAPTIVE_BOOST_FACTOR = 3.0  # Voix doit être 3x plus forte que le bruit

# Timing
SILENCE_BLOCKS_BEFORE_FLUSH = 3  # 1.5s de silence
MAX_PRODUCTION_SECONDS = 30.0

# Whisper
BEAM_SIZE = 5
VAD_FILTER = True
CONDITION_ON_PREVIOUS = True
```

### B. Dépendances à Ajouter

```txt
# requirements.txt
torch>=2.0.0
torchaudio>=2.0.0
noisereduce>=2.0.0
scipy>=1.10.0
pyannote.audio>=3.0.0  # Optionnel: speaker diarization
```

### C. Métriques de Performance à Suivre

| Métrique | Cible | Comment Mesurer |
|----------|-------|-----------------|
| Faux positifs VAD | < 5% | Compter transcriptions de bruit |
| Latence transcription | < 2s | Temps entre fin de parole et texte |
| WER (Word Error Rate) | < 10% | Comparer avec transcription manuelle |
| Mémoire utilisée | < 4GB | Monitorer pendant utilisation longue |

---

*Rapport généré le 2025-12-05 pour le projet micro_transcription*
