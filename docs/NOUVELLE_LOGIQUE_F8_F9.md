# Nouvelle Logique F8/F9 - Spécification

## Vue d'ensemble

Ce document décrit la nouvelle architecture de contrôle du système de transcription vocale.

---

## États du Système

| État | UI | Micro | VAD | Transcription |
|------|-----|-------|-----|---------------|
| **Système OFF** (veille) | Fermée | Désactivé | Non | Non |
| **Système ON + Micro ON** | Ouverte | Actif | Active | Auto (1-2s silence) |
| **Système ON + Micro OFF** | Ouverte | Désactivé | Non | Non |

---

## Contrôles

### F9 - Contrôle Principal (Système ON/OFF)

F9 est le **master switch** qui contrôle l'ensemble du système.

| Action | Transition | Effets |
|--------|------------|--------|
| F9 (OFF → ON) | Veille → Actif | 1. Démarrer le visualiseur (UI)<br>2. Activer le microphone<br>3. Activer la détection vocale (VAD) |
| F9 (ON → OFF) | Actif → Veille | 1. Fermer le visualiseur (UI)<br>2. Désactiver le microphone<br>3. Désactiver la VAD |

### F8 - Contrôle Micro (uniquement si système ON)

F8 contrôle uniquement le microphone quand le système est actif.

| Condition | Action F8 | Effet |
|-----------|-----------|-------|
| Système OFF | Appui F8 | **Ignoré** (aucun effet) |
| Système ON + Micro ON | Appui F8 | 1. Désactive le micro<br>2. **Force transcription immédiate** du buffer audio<br>3. Colle le texte au curseur |
| Système ON + Micro OFF | Appui F8 | Réactive le micro |

---

## Détection Vocale (VAD)

### Conditions d'activation

```
VAD active = Système ON + Micro ON
```

| État Système | État Micro | VAD Active |
|--------------|------------|------------|
| OFF | - | Non |
| ON | OFF | Non |
| ON | ON | **Oui** |

### Comportement

Quand la VAD est active :
1. Détection continue de la voix humaine
2. Accumulation de l'audio dans le buffer quand voix détectée
3. Déclenchement de la transcription après 1-2s de silence

---

## Déclenchement de la Transcription

Deux méthodes pour déclencher la transcription :

### 1. Automatique (silence détecté)

```
[Parole] → [Silence 1-2s] → [Transcription] → [Coller au curseur]
```

- La VAD détecte que l'utilisateur a arrêté de parler
- Après 1-2 secondes de silence continu
- L'audio accumulé est transcrit
- Le texte est collé à la position du curseur

### 2. Manuel (F8 désactive le micro)

```
[Parole] → [Appui F8] → [Transcription immédiate] → [Coller au curseur]
```

- L'utilisateur appuie sur F8 pour désactiver le micro
- Transcription immédiate du buffer audio (pas d'attente)
- Le texte est collé au curseur
- Le micro reste désactivé (F8 pour réactiver)

---

## Mode Veille Automatique

### Déclenchement (après 30 secondes)

La veille automatique se déclenche dans ces cas :

| Cas | Condition | Résultat |
|-----|-----------|----------|
| **A** | Micro ON mais aucune voix pendant 30s | → Veille auto |
| **B** | Micro OFF (via F8) depuis 30s | → Veille auto |
| **C** | Appui F9 | → Veille forcée (immédiate) |

### Effet de la veille auto

La veille automatique a le **même effet qu'un appui F9** :
- UI fermée
- Micro désactivé
- Nécessite F9 pour réactiver

### Pas d'auto-réveil

**Important** : L'auto-réveil sur détection de voix est **supprimé**.
- En veille, le micro est OFF donc aucune détection possible
- Seul F9 peut réactiver le système

---

## Mode Veille Profonde

### Déclenchement (après 30 minutes de veille)

```
[Veille normale] → [30 minutes] → [Veille profonde]
```

### Effets

| Ressource | Veille normale | Veille profonde |
|-----------|----------------|-----------------|
| Modèles Whisper | Chargés en RAM | **Déchargés** |
| Visualiseur | Fermé | Fermé |
| Micro | Désactivé | Désactivé |
| Réveil | Instantané | ~3-5 secondes |

---

## Diagramme d'états

```
                              ┌─────────────────────────────────────┐
                              │                                     │
                              ▼                                     │
┌──────────────────┐    F9    ┌──────────────────┐                  │
│                  │ ────────►│                  │                  │
│   SYSTÈME OFF    │          │  SYSTÈME ON      │                  │
│   (Veille)       │◄──────── │  Micro ON        │                  │
│                  │    F9    │  VAD Active      │                  │
└────────┬─────────┘          └────────┬─────────┘                  │
         │                             │                            │
         │                             │ F8                         │
         │ 30 min                      ▼                            │
         │                    ┌──────────────────┐                  │
         ▼                    │                  │     30s          │
┌──────────────────┐          │  SYSTÈME ON      │ ─────────────────┤
│                  │          │  Micro OFF       │                  │
│  VEILLE PROFONDE │          │  VAD Inactive    │                  │
│  (modèles        │          │                  │                  │
│   déchargés)     │          └────────┬─────────┘                  │
│                  │                   │                            │
└──────────────────┘                   │ F8                         │
                                       │                            │
                                       ▼                            │
                              ┌──────────────────┐                  │
                              │  Retour à        │                  │
                              │  Micro ON        │──────────────────┘
                              └──────────────────┘       30s silence
```

---

## Timeline typique

```
T=0     [F9] Système démarre (UI + Micro + VAD)
        │
T=1     [Utilisateur parle] → Buffer accumule l'audio
        │
T=5     [Silence détecté]
        │
T=6.5   [1.5s silence] → Transcription → Coller
        │
T=10    [Utilisateur parle à nouveau]
        │
T=15    [F8] Force transcription → Coller → Micro OFF
        │
T=45    [30s micro OFF] → Veille auto
        │
T=60    [F9] Réactivation système
```

---

## Indicateurs UI

L'interface affiche clairement :

### 1. État du Micro (F8)
- 🎤 **Rouge pulsant** : Micro actif, en écoute
- ⏸️ **Gris** : Micro en pause

### 2. État VAD
- 🟢 **Vert** : Voix détectée (parole en cours)
- ⚫ **Gris** : Silence / En attente

### 3. État Traitement
- ⏳ **Spinner** : Transcription en cours
- ✅ **Check** : Transcription terminée (bref flash)

### Layout proposé

```
┌─────────────────────────────────────────────────────────────┐
│  🎤  [Micro]  │  🟢 VAD  │  ⏳ Processing  │  Status...     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    [Waveform Visualizer]                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  "Texte de prévisualisation en temps réel..."              │
└─────────────────────────────────────────────────────────────┘
```

---

## Configuration

```python
# shared/config.py

# Délai de silence avant transcription automatique
SILENCE_BEFORE_TRANSCRIBE_SECONDS = 1.5  # 1-2 secondes

# Délai d'inactivité avant veille automatique
AUTO_SLEEP_SECONDS = 30.0  # 30 secondes

# Délai avant veille profonde (déchargement modèles)
DEEP_SLEEP_SECONDS = 1800  # 30 minutes
```

---

## Résumé des changements

| Aspect | Avant | Après |
|--------|-------|-------|
| F9 | Toggle veille (UI reste ouverte) | Toggle système complet (UI + Micro) |
| F8 | Toggle micro indépendant | Toggle micro + force transcription si OFF |
| Auto-réveil | Activé sur détection voix | **Supprimé** |
| Auto-sleep trigger | Inactivité voix seulement | Inactivité voix OU micro OFF |
| Délai auto-sleep | 10 secondes | 30 secondes |
| Délai deep sleep | 10 minutes | 30 minutes |
| Transcription auto | Sur silence prolongé | Sur silence 1-2s |
| Force transcription | Non | Oui (via F8 OFF) |
