"""Test standalone du serveur SSE pour debug."""

import time
import queue
import threading
from flask import Flask, Response

app = Flask(__name__)
app.logger.disabled = True

_sse_clients = []
_sse_lock = threading.Lock()

def event_stream():
    """Générateur SSE."""
    messages = queue.Queue()
    with _sse_lock:
        _sse_clients.append(messages)
        print(f"[SSE] Client connecté. Total: {len(_sse_clients)}")
    
    try:
        while True:
            msg = messages.get()
            if msg is None:
                break
            print(f"[SSE] Envoi: '{msg}'")
            yield f"data: {msg}\n\n"
    finally:
        with _sse_lock:
            _sse_clients.remove(messages)
            print(f"[SSE] Client déconnecté. Restant: {len(_sse_clients)}")

@app.route('/events')
def sse():
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/ping')
def ping():
    return 'pong'

def broadcast(text: str):
    """Diffuse un message."""
    with _sse_lock:
        print(f"[BROADCAST] À {len(_sse_clients)} client(s): '{text}'")
        for client in _sse_clients:
            try:
                client.put_nowait(text)
            except queue.Full:
                pass

def start_server():
    """Démarre le serveur Flask."""
    from werkzeug.serving import make_server
    server = make_server('127.0.0.1', 5432, app, threaded=True)
    print("🌐 Serveur SSE démarré sur http://127.0.0.1:5432")
    server.serve_forever()

if __name__ == "__main__":
    # Démarrer serveur dans un thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    print("Serveur démarré. Attendez 2 secondes...")
    time.sleep(2)
    
    print("\n📨 Test d'envoi de messages toutes les 2 secondes...")
    print("Ouvrez http://127.0.0.1:5432/events dans un navigateur ou avec curl")
    print("Ou lancez le visualizer pour tester la connexion SSE")
    print("\nAppuyez sur Ctrl+C pour arrêter\n")
    
    try:
        counter = 0
        while True:
            counter += 1
            msg = f"Message de test #{counter} - {time.strftime('%H:%M:%S')}"
            broadcast(msg)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\n✅ Test terminé")
