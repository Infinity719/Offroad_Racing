# server_hillclimb.py
from flask import Flask, request
from flask_socketio import SocketIO, emit
import threading, time, random, math, os

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# -----------------------
# Config
TERRAIN_LENGTH = 8000
TERRAIN_FREQ = 0.01
TERRAIN_AMPLITUDE = 120
TERRAIN_VARIANCE = 6
BROADCAST_HZ = 30
TERRAIN_SEED = 12345

# Shared game state
players = {}
terrain = []

def generate_terrain(length=TERRAIN_LENGTH, freq=TERRAIN_FREQ, amp=TERRAIN_AMPLITUDE, var=TERRAIN_VARIANCE, start_height=380):
    rng = random.Random(TERRAIN_SEED)
    t = []
    for x in range(length):
        y = start_height + math.sin(x * freq) * amp + rng.randint(-var, var)
        t.append((x, int(y)))
    return t

terrain = generate_terrain()

def spawn_player(pid):
    start_x = 100 + (len(players) * 30)
    return {
        "id": pid,
        "x": float(start_x),
        "y": float(terrain[int(start_x)][1] - 30),
        "vx": 0.0,
        "vy": 0.0,
        "distance": float(start_x),
        "color": (random.randint(50,255), random.randint(50,255), random.randint(50,255)),
        "nickname": f"Player{len(players)+1}",
        "on_ground": True,
        "last_update": time.time(),
    }

@app.route("/")
def index():
    return "Hill Climb Racing Server Running."

@socketio.on('connect')
def handle_connect():
    pid = request.sid
    p = spawn_player(pid)
    players[pid] = p
    emit('init', {"your_id": pid, "terrain": terrain, "players": players})
    emit('player_joined', {"id": pid, "player": p}, broadcast=True, include_self=False)

@socketio.on('disconnect')
def handle_disconnect():
    pid = request.sid
    if pid in players:
        players.pop(pid)
        emit('player_left', {"id": pid}, broadcast=True)

@socketio.on('player_update')
def handle_player_update(data):
    pid = request.sid
    if pid not in players:
        players[pid] = spawn_player(pid)
    p = players[pid]
    try:
        p['x'] = float(data.get('x', p['x']))
        p['y'] = float(data.get('y', p['y']))
        p['vx'] = float(data.get('vx', p['vx']))
        p['vy'] = float(data.get('vy', p['vy']))
        p['distance'] = float(data.get('distance', p['distance']))
        p['color'] = tuple(data.get('color', p['color']))
        p['nickname'] = data.get('nickname', p['nickname'])
        p['last_update'] = time.time()
    except Exception:
        pass

def broadcast_loop():
    interval = 1.0 / BROADCAST_HZ
    while True:
        snapshot = {pid: {"x": p['x'], "y": p['y'], "vx": p['vx'], "vy": p['vy'],
                          "distance": p['distance'], "color": p['color'], "nickname": p['nickname']}
                    for pid, p in players.items()}
        socketio.emit('game_state', {"players": snapshot})
        time.sleep(interval)

if __name__ == '__main__':
    threading.Thread(target=broadcast_loop, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)