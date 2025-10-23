# Visualiseur Audio Indépendant

Visualiseur d'ondes audio en temps réel avec interface web. Fonctionne de manière autonome et peut être contrôlé via API REST.

## 🚀 Démarrage Rapide

### Installation des dépendances

```bash
pip install -r visualizer/requirements.txt
```

### Lancement du serveur

```bash
# Méthode 1: Script standalone (recommandé)
python run_visualizer.py

# Méthode 2: Module Python
python -m visualizer.server

# Méthode 3: Port personnalisé
python run_visualizer.py 8080

# Méthode 4: Host et port personnalisés
python run_visualizer.py 8080 0.0.0.0
```

Le serveur démarrera sur `http://127.0.0.1:5500` par défaut.

### Accès à l'interface web

Ouvrez votre navigateur et accédez à:
```
http://127.0.0.1:5500
```

## 📡 API REST

Le visualiseur expose une API REST pour permettre le contrôle externe.

### Endpoints

#### `POST /api/preview`
Affiche du texte de preview dans le visualiseur.

**Body:**
```json
{
  "text": "Texte à afficher"
}
```

**Response:**
```json
{
  "status": "ok",
  "text": "Texte à afficher"
}
```

#### `POST /api/state`
Change l'état du visualiseur (actif/veille).

**Body:**
```json
{
  "state": "sleep"  // "active" ou "sleep"
}
```

**Response:**
```json
{
  "status": "ok",
  "state": "sleep"
}
```

#### `GET /api/status`
Récupère le statut actuel du visualiseur.

**Response:**
```json
{
  "status": "active",
  "preview_text": "Dernière transcription...",
  "connected_clients": 1
}
```

#### `POST /api/clear`
Efface le texte de preview.

**Response:**
```json
{
  "status": "ok"
}
```

#### `GET /ping`
Healthcheck endpoint.

**Response:**
```
pong
```

#### `GET /events`
SSE (Server-Sent Events) pour recevoir les mises à jour en temps réel.

## 🐍 Client Python

Le module inclut un client Python pour faciliter l'interaction avec l'API.

### Utilisation basique

```python
from visualizer.client import VisualizerClient

# Créer un client
client = VisualizerClient(host="127.0.0.1", port=5500)

# Vérifier si le serveur est accessible
if client.ping():
    print("Serveur accessible!")

# Envoyer du texte de preview
client.send_preview("Bonjour, ceci est un test")

# Changer l'état
client.set_state("sleep")
client.set_state("active")

# Récupérer le statut
status = client.get_status()
print(status)

# Effacer le preview
client.clear_preview()
```

### Fonctions de commodité

```python
from visualizer import client

# Fonctions simples sans créer explicitement un client
client.send_preview("Hello world")
client.set_state("active")
status = client.get_status()
```

## 🔧 Configuration

La configuration se trouve dans `visualizer/config.py`:

```python
# Server configuration
HOST = "127.0.0.1"
PORT = 5500

# API configuration
API_PREFIX = "/api"

# CORS settings
CORS_ENABLED = True
CORS_ORIGINS = "*"

# Debug mode
DEBUG = False
```

## 🔗 Intégration avec transcription_app

Pour intégrer le visualiseur avec votre application de transcription:

```python
from visualizer.client import VisualizerClient

# Créer un client
viz = VisualizerClient()

# Vérifier la connexion
if not viz.ping():
    print("Visualiseur non disponible")
    return

# Envoyer des mises à jour de transcription
def on_transcription_update(text: str):
    viz.send_preview(text)

# Signaler les changements d'état
def on_sleep_mode():
    viz.set_state("sleep")

def on_active_mode():
    viz.set_state("active")
```

## 🌐 Utilisation depuis d'autres langages

Le visualiseur expose une API REST standard, vous pouvez donc l'utiliser depuis n'importe quel langage.

### JavaScript/Node.js

```javascript
// Envoyer du texte de preview
fetch('http://127.0.0.1:5500/api/preview', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: 'Hello from JS' })
});

// Changer l'état
fetch('http://127.0.0.1:5500/api/state', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ state: 'sleep' })
});
```

### cURL

```bash
# Envoyer du texte
curl -X POST http://127.0.0.1:5500/api/preview \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from cURL"}'

# Changer l'état
curl -X POST http://127.0.0.1:5500/api/state \
  -H "Content-Type: application/json" \
  -d '{"state": "sleep"}'

# Récupérer le statut
curl http://127.0.0.1:5500/api/status

# Ping
curl http://127.0.0.1:5500/ping
```

## 🧑‍💻 Mode développement

Pour activer le mode debug:

```python
# Dans visualizer/config.py
DEBUG = True
```

Ou en passant le paramètre au lancement:

```python
from visualizer.server import run_server

run_server(debug=True)
```

## 📦 Architecture

```
visualizer/
├── __init__.py          # Module init
├── config.py            # Configuration
├── app.py               # Flask app avec API REST
├── client.py            # Client HTTP Python
├── server.py            # Launcher du serveur
├── static/
│   ├── css/
│   │   └── visualizer.css
│   └── js/
│       └── visualizer.js
├── templates/
│   └── index.html
└── README.md           # Ce fichier
```

## ❓ FAQ

**Q: Comment changer le port du serveur?**
A: Passez le port en argument: `python run_visualizer.py 8080`

**Q: Le visualiseur peut-il être accessible depuis un autre ordinateur?**
A: Oui, lancez avec l'host `0.0.0.0`: `python run_visualizer.py 5500 0.0.0.0`

**Q: Comment intégrer avec mon application existante?**
A: Utilisez le client Python (`visualizer.client`) ou faites des requêtes HTTP directement à l'API REST.

**Q: Est-ce que le visualiseur nécessite Qt/PySide6?**
A: Non! Le visualiseur web est complètement indépendant et ne nécessite que Flask. Il fonctionne dans n'importe quel navigateur moderne.
