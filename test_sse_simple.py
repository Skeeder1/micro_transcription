"""
Test SSE ultra-simple pour vérifier Flask SSE fonctionne
"""
from flask import Flask, Response
import time

app = Flask(__name__)

def event_stream():
    """Générateur SSE simple."""
    count = 0
    while True:
        count += 1
        message = f"Test message {count} - {time.strftime('%H:%M:%S')}"
        print(f"[SSE] Envoi: {message}")
        yield f"data: {message}\n\n"
        time.sleep(2)

@app.route('/events')
def sse():
    """Endpoint SSE."""
    response = Response(event_stream(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/ping')
def ping():
    """Test connexion."""
    return 'pong'

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TEST SSE SIMPLE")
    print("=" * 60)
    print(f"Serveur démarré sur http://127.0.0.1:5432")
    print(f"Ouvrez test_sse_client.html dans votre navigateur")
    print(f"Ou testez avec: curl http://127.0.0.1:5432/ping")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5432, debug=False, threaded=True)
