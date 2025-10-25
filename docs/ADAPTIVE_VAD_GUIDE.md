# Guide : Détection Adaptative pour Environnements Bruyants

## Problème résolu

❌ **Avant** : La musique/bruit ambiant empêchait la détection de fin de parole (transcription bloquée 20-30s)

✅ **Après** : Le système détecte quand VOUS parlez par-dessus le bruit ambiant grâce à la **détection adaptative**

## Comment ça marche

### Principe de base

Au lieu de détecter "voix vs silence", le système détecte **"NOUVELLE voix par-dessus bruit ambiant"** :

```
1. Calibration (2 premières secondes)
   → Mesure le niveau de bruit ambiant (musique, conversations, etc.)

2. Détection de pic d'énergie
   → Votre voix doit être 2.5x plus forte que le bruit ambiant

3. Confirmation Silero VAD
   → Vérifie que c'est bien de la voix humaine

4. Fin de parole
   → Détectée quand le niveau redescend proche du bruit ambiant
```

### Configuration actuelle

Dans `core/config.py`, le mode adaptatif est **déjà activé** :

```python
# Mode adaptatif (ACTIVÉ par défaut)
USE_ADAPTIVE_DETECTION = True

# Facteur de boost requis (2.5x = équilibré)
ADAPTIVE_BOOST_FACTOR = 2.5
```

## Utilisation

### 1. Lancement normal

```bash
scripts\start_transcription.bat
```

**Les 2 premières secondes** :
- NE PARLEZ PAS pendant la calibration
- Le système mesure le bruit ambiant (musique, conversations, etc.)
- Vous verrez : `🎯 Calibration terminée: niveau ambiant = 0.XXX`

**Après calibration** :
- Parlez normalement
- Le système détecte quand vous commencez à parler (pic d'énergie)
- La transcription se déclenche MÊME avec musique/bruit en fond

### 2. Mode debug (recommandé pour réglage)

Pour voir comment le système fonctionne :

```python
# core/config.py
DEBUG_VAD = True
```

Vous verrez en temps réel :
```
[VAD] REF=0.045 NOW=0.047 BOOST=1.04x → AMBIANT (musique seule)
[VAD] ✓ VOIX: REF=0.045 NOW=0.135 BOOST=3.00x Silero=0.876 (vous parlez)
[VAD] REF=0.047 NOW=0.048 BOOST=1.02x → AMBIANT (vous arrêtez)
```

## Réglage du facteur de boost

Si le système ne fonctionne pas bien avec votre environnement :

### Problème : Musique détectée comme voix

```python
# Augmentez le facteur de boost
ADAPTIVE_BOOST_FACTOR = 3.0  # Plus strict (voix doit être 3x plus forte)
```

### Problème : Voix non détectée

```python
# Baissez le facteur de boost
ADAPTIVE_BOOST_FACTOR = 2.0  # Plus sensible (voix 2x plus forte suffit)
```

### Recommandations par environnement

| Environnement | Boost Factor | Description |
|---------------|--------------|-------------|
| Bureau calme | 2.0 | Peu de bruit, détection facile |
| **Bureau/café avec musique** | **2.5** | **Recommandé (défaut)** |
| Café très bruyant | 3.0 | Beaucoup de conversations |
| Open space | 3.5 | Environnement très bruyant |

## Test avant utilisation réelle

Avant de lancer l'application complète :

```bash
.venv\Scripts\python.exe scripts\test_vad.py
```

Sortie attendue :
```
[OK] VoiceDetector initialise (mode adaptatif)
🎯 Calibration terminée: niveau ambiant = 0.049
[VAD] REF=0.050 NOW=0.049 BOOST=0.99x → AMBIANT ✓
```

## Comparaison Avant/Après

### Scénario : Musique en arrière-plan

**Mode legacy (ancien)** :
```
1. Musique joue (RMS=0.05)
   → Silero VAD détecte "voix" (musique contient fréquences vocales)
   → Système pense que c'est de la parole

2. Vous parlez et arrêtez
   → Musique continue
   → Système attend silence absolu
   → Transcription bloquée 20-30 secondes ❌
```

**Mode adaptatif (nouveau)** :
```
1. Calibration : mesure musique = 0.05

2. Musique seule (RMS=0.05)
   → BOOST = 0.05/0.05 = 1.0x < 2.5x requis
   → Rejeté comme bruit ambiant ✓

3. Vous parlez (RMS=0.15)
   → BOOST = 0.15/0.05 = 3.0x > 2.5x requis
   → Silero confirme = voix humaine
   → Détection réussie ✓

4. Vous arrêtez (RMS retourne à ~0.05)
   → BOOST = 0.05/0.05 = 1.0x < 2.5x
   → Fin de parole détectée
   → Transcription déclenchée immédiatement ✓
```

## Désactivation

Pour revenir au mode legacy (seuils fixes) :

```python
# core/config.py
USE_ADAPTIVE_DETECTION = False
```

Le système utilisera alors :
- RMS threshold simple
- Silero VAD avec seuil fixe
- Pas d'adaptation au bruit ambiant

## Métriques de debug

Avec `DEBUG_VAD = True`, voici ce que signifient les valeurs :

- **REF** : Niveau de référence (bruit ambiant moyen)
- **NOW** : Niveau audio actuel
- **BOOST** : Ratio NOW/REF (combien de fois plus fort que le bruit)
- **Silero** : Probabilité de voix selon le modèle ML (0.0-1.0)

**Exemple de bonne détection** :
```
[VAD] ✓ VOIX: REF=0.045 NOW=0.135 BOOST=3.00x Silero=0.876
       ^       ^         ^         ^           ^
       OK      Bruit     Actuel    3x plus     88% voix
                                   fort
```

## Calibration manuelle

Si l'environnement change beaucoup, relancez l'application :
1. Arrêtez : `scripts\stop_transcription.bat`
2. Relancez : `scripts\start_transcription.bat`
3. Nouvelle calibration automatique (2s)

## Limites

Le système adaptatif fonctionne bien pour :
- ✅ Musique/TV en fond constant
- ✅ Conversations lointaines
- ✅ Bruits mécaniques (ventilateur, clavier)

Moins bien pour :
- ⚠️ Bruits très variables (porte qui claque pendant que vous parlez)
- ⚠️ Parole chuchotée avec musique forte (boost factor insuffisant)

Dans ces cas, utilisez `ADAPTIVE_BOOST_FACTOR` plus bas ou passez en mode legacy.

## Support

Si vous rencontrez des problèmes :
1. Activez `DEBUG_VAD = True`
2. Observez les valeurs de BOOST et Silero
3. Ajustez `ADAPTIVE_BOOST_FACTOR` selon vos observations
4. Consultez le guide principal : `docs/VAD_GUIDE.md`
