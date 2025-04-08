import socket
import threading
import random
import time

# Khởi tạo mê cung (0: trống, 1: tường)
MAZE_WIDTH, MAZE_HEIGHT = 32, 16
maze = [[1 if random.random() < 0.2 else 0 for _ in range(MAZE_WIDTH)] for _ in range(MAZE_HEIGHT)]
for i in range(MAZE_WIDTH):  # Viền tường
    maze[0][i] = maze[MAZE_HEIGHT-1][i] = 1
for i in range(MAZE_HEIGHT):
    maze[i][0] = maze[i][MAZE_WIDTH-1] = 1

# Trạng thái trò chơi
players = {}  # {player_id: {"x": x, "y": y, "dir": dir, "score": score}}
bullets = []  # [{"x": x, "y": y, "dir": dir, "owner": player_id}]
lock = threading.Lock()

def is_valid_move(x, y):
    return 0 <= x < MAZE_WIDTH and 0 <= y < MAZE_HEIGHT and maze[y][x] == 0

def spawn_player():
    while True:
        x, y = random.randint(1, MAZE_WIDTH-2), random.randint(1, MAZE_HEIGHT-2)
        if is_valid_move(x, y):
            return x, y

def handle_client(conn, addr):
    player_id = f"{addr[0]}:{addr[1]}"
    with lock:
        x, y = spawn_player()
        players[player_id] = {"x": x, "y": y, "dir": "right", "score": 0, "last_shot": 0}
    print(f"New player {player_id} connected")

    try:
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            action = data.strip()

            with lock:
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
                elif action == "shoot" and time.time() - player["last_shot"] >= 0.4:  # 4 cells delay
                    bullets.append({"x": player["x"], "y": player["y"], "dir": player["dir"], "owner": player_id})
                    player["score"] -= 1
                    player["last_shot"] = time.time()

                if is_valid_move(new_x, new_y) and not any(p["x"] == new_x and p["y"] == new_y for p in players.values() if p != player):
                    player["x"], player["y"] = new_x, new_y

                # Gửi trạng thái trò chơi
                state = {"maze": maze, "players": players, "bullets": bullets}
                conn.send(str(state).encode())
    except:
        pass
    finally:
        with lock:
            del players[player_id]
        conn.close()
        print(f"Player {player_id} disconnected")

def update_bullets():
    while True:
        with lock:
            for bullet in bullets[:]:
                if bullet["dir"] == "up": bullet["y"] -= 1
                elif bullet["dir"] == "down": bullet["y"] += 1
                elif bullet["dir"] == "left": bullet["x"] -= 1
                elif bullet["dir"] == "right": bullet["x"] += 1

                # Kiểm tra va chạm
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
        time.sleep(0.1)  # Đạn nhanh gấp 4 lần (0.1s vs 0.4s di chuyển)

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 5555))
    server.listen(5)
    print("Server started on port 5555")

    threading.Thread(target=update_bullets, daemon=True).start()

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    start_server()