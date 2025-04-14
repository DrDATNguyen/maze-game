import socket
import threading
import random
import time
import queue
import copy

# Khởi tạo mê cung
MAZE_WIDTH, MAZE_HEIGHT = 32, 16
maze = [[1 if random.random() < 0.2 else 0 for _ in range(MAZE_WIDTH)] for _ in range(MAZE_HEIGHT)]
for i in range(MAZE_WIDTH):
    maze[0][i] = maze[MAZE_HEIGHT-1][i] = 1
for i in range(MAZE_HEIGHT):
    maze[i][0] = maze[i][MAZE_WIDTH-1] = 1

# Trạng thái trò chơi
players = {}
bullets = []
lock = threading.Lock()
clients = []
action_queue = queue.Queue()
last_state = None

def is_valid_move(x, y):
    return 0 <= x < MAZE_WIDTH and 0 <= y < MAZE_HEIGHT and maze[y][x] == 0

def spawn_player():
    while True:
        x, y = random.randint(1, MAZE_WIDTH-2), random.randint(1, MAZE_HEIGHT-2)
        if is_valid_move(x, y):
            return x, y

def handle_client(conn, addr):
    player_id = f"{addr[0]}:{addr[1]}"
    lock_acquire_time = time.time()
    with lock:
        pre_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
        x, y = spawn_player()
        players[player_id] = {"x": x, "y": y, "dir": "right", "score": 0, "last_shot": 0}
        clients.append(conn)
        post_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
        if pre_lock_state != post_lock_state:
            print(f"Locking in handle_client for adding player {player_id} at {lock_acquire_time}")
            print(f"Unlocked in handle_client after adding player {player_id} at {time.time()}")
    print(f"New player {player_id} connected")

    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            action = data.strip()
            print(f"Received from client {player_id}: {action}")
            
            lock_acquire_time = time.time()
            with lock:
                pre_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
                action_queue.put((player_id, action))
                post_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
                # Không in lock/unlock vì enqueue không sửa trạng thái
                print(f"Enqueued action: player={player_id}, action={action}")

    except:
        pass
    finally:
        lock_acquire_time = time.time()
        with lock:
            pre_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
            if player_id in players:
                del players[player_id]
            if conn in clients:
                clients.remove(conn)
            post_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
            if pre_lock_state != post_lock_state:
                print(f"Locking in handle_client for removing player {player_id} at {lock_acquire_time}")
                print(f"Unlocked in handle_client after removing player {player_id} at {time.time()}")
        conn.close()
        print(f"Player {player_id} disconnected")

def process_actions():
    while True:
        try:
            player_id, action = action_queue.get(block=True, timeout=0.1)
            print(f"Dequeued action: player={player_id}, action={action}")
            
            lock_acquire_time = time.time()
            with lock:
                pre_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
                if player_id not in players:
                    continue
                player = players[player_id]
                new_x, new_y = player["x"], player["y"]

                if action == "up":
                    new_y -= 1
                    player["dir"] = "up"
                elif action == "down":
                    new_y += 1
                    player["dir"] = "down"
                elif action == "left":
                    new_x -= 1
                    player["dir"] = "left"
                elif action == "right":
                    new_x += 1
                    player["dir"] = "right"
                elif action == "shoot" and time.time() - player["last_shot"] >= 0.4:
                    bullets.append({"x": player["x"], "y": player["y"], "dir": player["dir"], "owner": player_id})
                    player["score"] -= 1
                    player["last_shot"] = time.time()

                if is_valid_move(new_x, new_y) and not any(p["x"] == new_x and p["y"] == new_y for p in players.values() if p != player):
                    player["x"], player["y"] = new_x, new_y
                post_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
                if pre_lock_state != post_lock_state:
                    print(f"Locking in process_actions for action {action} by {player_id} at {lock_acquire_time}")
                    print(f"Unlocked in process_actions after processing action {action} at {time.time()}")
            
            action_queue.task_done()
        except queue.Empty:
            time.sleep(0.01)

def update_bullets():
    while True:
        lock_acquire_time = time.time()
        with lock:
            pre_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
            for bullet in bullets[:]:
                if bullet["dir"] == "up": bullet["y"] -= 1
                elif bullet["dir"] == "down": bullet["y"] += 1
                elif bullet["dir"] == "left": bullet["x"] -= 1
                elif bullet["dir"] == "right": bullet["x"] += 1

                if not (0 <= bullet["x"] < MAZE_WIDTH and 0 <= bullet["y"] < MAZE_HEIGHT) or maze[bullet["y"]][bullet["x"]] == 1:
                    bullets.remove(bullet)
                    continue

                for pid, p in players.items():
                    if p["x"] == bullet["x"] and p["y"] == bullet["y"] and pid != bullet["owner"]:
                        p["score"] -= 5
                        players[bullet["owner"]]["score"] += 11
                        x, y = spawn_player()
                        p["x"], p["y"] = x, y
                        p["dir"] = random.choice(["up", "down", "left", "right"])
                        while maze[p["y"]][p["x"]] == 1 or p["dir"] == "up" and p["y"] == 0:
                            p["dir"] = random.choice(["up", "down", "left", "right"])
                        bullets.remove(bullet)
                        break
            post_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
            if pre_lock_state != post_lock_state:
                print(f"Locking in update_bullets at {lock_acquire_time}")
                print(f"Unlocked in update_bullets at {time.time()}")
        time.sleep(0.1)

def broadcast_state():
    global last_state
    while True:
        lock_acquire_time = time.time()
        with lock:
            pre_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
            state = {"maze": maze, "players": copy.deepcopy(players), "bullets": copy.deepcopy(bullets)}
            if last_state is None or state["players"] != last_state["players"] or state["bullets"] != last_state["bullets"]:
                print(f"Sending to clients: Players={len(state['players'])}, Bullets={len(state['bullets'])}")
                last_state = copy.deepcopy(state)
                for conn in clients[:]:
                    try:
                        conn.send(str(state).encode())
                    except:
                        pass
            post_lock_state = (copy.deepcopy(players), copy.deepcopy(bullets), copy.copy(clients))
            if pre_lock_state != post_lock_state:
                print(f"Locking in broadcast_state at {lock_acquire_time}")
                print(f"Unlocked in broadcast_state at {time.time()}")
        time.sleep(0.1)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)
    print("Server started on port 5555")

    threading.Thread(target=update_bullets, daemon=True).start()
    threading.Thread(target=broadcast_state, daemon=True).start()
    threading.Thread(target=process_actions, daemon=True).start()

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()