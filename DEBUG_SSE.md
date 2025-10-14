# 🔍 DEBUG SSE - Preview ne s'affiche pas

## 🔴 Problème

Le texte preview ne s'affiche pas dans la zone "En attente de parole..." du visualizer.

## 🧪 Tests à effectuer

### **Test 1 : Vérifier serveur SSE**

```bash
# Terminal 1 : Lancer le serveur de test
C:\GitHub\transcription-audio\.venv\Scripts\python.exe test_sse_server.py

# Attendu :
# 🌐 Serveur SSE démarré sur http://127.0.0.1:5432
# 📨 Test d'envoi de messages toutes les 2 secondes...
```

**Vérification** :
- Ouvrir navigateur : `http://127.0.0.1:5432/ping`
- Doit afficher : `pong`

### **Test 2 : Vérifier réception SSE dans navigateur**

```bash
# Serveur test_sse_server.py doit être lancé

# Ouvrir dans un navigateur :
test_sse_client.html
```

**Vérification** :
- Status doit devenir "✅ Connecté"
- Messages doivent apparaître toutes les 2 secondes
- Si ça marche → SSE fonctionne, problème dans visualizer Qt
- Si ça ne marche pas → SSE ne fonctionne pas, problème serveur

### **Test 3 : Vérifier avec curl**

```bash
# Serveur test_sse_server.py doit être lancé

# Dans un nouveau terminal :
curl http://127.0.0.1:5432/events
```

**Attendu** :
```
data: Message de test #1 - 14:35:21

data: Message de test #2 - 14:35:23

data: Message de test #3 - 14:35:25
...
```

### **Test 4 : Logs main_enhanced.py**

```bash
# Lancer main_enhanced.py
C:\GitHub\transcription-audio\.venv\Scripts\python.exe main_enhanced.py

# Observer les logs :
```

**Chercher dans les logs** :

```
✅ BON :
[SSE] Nouveau client connecté. Total: 1
[TEST] Envoi message de test SSE...
[SSE] Envoi à 1 client(s): '🔊 Système prêt...'

❌ MAUVAIS :
[SSE] Aucun client connecté pour recevoir: '🔊 Système prêt...'
```

Si "Aucun client connecté" → Le visualizer ne se connecte pas au serveur SSE

### **Test 5 : Vérifier console JS du visualizer**

Dans le code du visualizer, les logs JS doivent afficher :

```javascript
[SSE] Connecting to http://127.0.0.1:5432/events
[SSE] Connected
[SSE] Received: ...
```

Si pas de logs `[SSE] Connected` → Problème de connexion côté visualizer

## 🔧 Solutions possibles

### **Solution 1 : Port occupé**

```bash
# Vérifier si le port 5432 est disponible
netstat -ano | findstr :5432

# Si occupé, changer le port dans :
# - main_enhanced.py : SSE_PORT = 5433
# - mic_visualizer_enhanced.py : sse_port argument
```

### **Solution 2 : Firewall bloque**

```bash
# Tester en local d'abord
curl http://127.0.0.1:5432/ping

# Si ça marche, le firewall n'est probablement pas le problème
```

### **Solution 3 : CORS (si navigateur)**

Ajouter headers CORS dans main_enhanced.py :

```python
@app.route('/events')
def sse():
    response = Response(event_stream(), mimetype='text/event-stream')
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Cache-Control'] = 'no-cache'
    return response
```

### **Solution 4 : Ordre de démarrage**

Le visualizer doit démarrer **APRÈS** le serveur SSE :

```python
# Dans main()
start_sse_server()
time.sleep(0.5)  # Attendre serveur
start_visualizer()
time.sleep(1.0)  # Attendre connexion visualizer
```

### **Solution 5 : Vérifier EventSource dans visualizer**

Dans `mic_visualizer_enhanced.py`, le HTML doit contenir :

```javascript
const connectSSE = () => {
    console.log('[SSE] Connecting to http://127.0.0.1:5432/events');
    
    eventSource = new EventSource('http://127.0.0.1:5432/events');
    
    eventSource.onopen = () => {
        console.log('[SSE] Connected');
        // ...
    };
    
    eventSource.onmessage = (event) => {
        console.log('[SSE] Received:', event.data);
        updatePreview(event.data);
    };
};
```

## 📋 Checklist de diagnostic

### Serveur SSE
- [ ] `test_sse_server.py` démarre sans erreur
- [ ] `curl http://127.0.0.1:5432/ping` retourne `pong`
- [ ] `curl http://127.0.0.1:5432/events` affiche des messages
- [ ] `test_sse_client.html` reçoit les messages

### Main enhanced
- [ ] Serveur SSE démarre (log "🌐 Serveur SSE démarré")
- [ ] Visualizer démarre après serveur
- [ ] Log "[SSE] Nouveau client connecté" apparaît
- [ ] Log "[SSE] Envoi à X client(s)" apparaît quand vous parlez

### Visualizer
- [ ] Fenêtre s'ouvre
- [ ] Waveform s'affiche
- [ ] Zone preview visible (en bas)
- [ ] Indicateur SSE devient vert
- [ ] Console JS (si accessible) affiche "[SSE] Connected"

## 🎯 Diagnostic rapide

**Si serveur test fonctionne mais pas main_enhanced** :
→ Problème : Timing ou ordre de démarrage
→ Solution : Augmenter `time.sleep()` après `start_sse_server()`

**Si rien ne fonctionne (même test_sse_server)** :
→ Problème : Flask, port, ou firewall
→ Solution : Vérifier port libre, tester autre port

**Si serveur fonctionne mais visualizer ne reçoit pas** :
→ Problème : EventSource dans visualizer
→ Solution : Vérifier code JS du visualizer

**Si client HTML test fonctionne mais pas visualizer Qt** :
→ Problème : Qt WebEngine bloque SSE
→ Solution : Vérifier permissions Qt, ou utiliser polling à la place

## 📝 Logs ajoutés pour debug

Dans `main_enhanced.py`, j'ai ajouté :

1. **event_stream()** :
   ```python
   print(f"[SSE] Nouveau client connecté. Total: {len(_sse_clients)}")
   print(f"[SSE] Envoi message: '{msg[:50]}...'")
   print(f"[SSE] Client déconnecté. Restant: {len(_sse_clients)}")
   ```

2. **broadcast_preview()** :
   ```python
   if num_clients == 0:
       print(f"\n[SSE] Aucun client connecté pour recevoir: '{text[:50]}...'")
   else:
       print(f"\n[SSE] Envoi à {num_clients} client(s): '{text[:50]}...'")
   ```

3. **main()** :
   ```python
   broadcast_preview("🔊 Système prêt - Parlez maintenant!")
   ```

Ces logs permettent de tracer exactement où est le problème.

## ✅ Prochaines étapes

1. **Lancer test_sse_server.py**
2. **Ouvrir test_sse_client.html**
3. **Vérifier réception messages**
4. **Si OK** → Problème dans visualizer Qt
5. **Si KO** → Problème dans serveur SSE

---

**Fichiers créés pour debug** :
- ✅ `test_sse_server.py` - Serveur SSE standalone
- ✅ `test_sse_client.html` - Client test navigateur
- ✅ `DEBUG_SSE.md` - Ce guide

**Prochaine action** : Lancer les tests ci-dessus
