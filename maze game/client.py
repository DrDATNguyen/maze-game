import pygame
import socket
import ast
import threading
import random
import os
import queue
import copy

# Khởi tạo Pygame
pygame.init()
CELL_SIZE = 30
WIDTH, HEIGHT = 32 * CELL_SIZE, 16 * CELL_SIZE
screen = pygame.display.set_mode((WIDTH, HEIGHT + 100))
pygame.display.set_caption("Maze War")
clock = pygame.time.Clock()

# Kết nối server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 5555))  # Thay bằng IP của máy bạn

# Tải hình ảnh xe tăng từ thư mục image
image_dir = "image"
tank_images = []
for filename in os.listdir(image_dir):
    if filename.endswith(".png") or filename.endswith(".jpg"):
        img = pygame.image.load(os.path.join(image_dir, filename))
        img = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))
        tank_images.append(img)

if not tank_images:
    raise Exception("No tank images found in 'image' folder!")

# Gán ngẫu nhiên một hình xe tăng cho client này
my_tank_image = random.choice(tank_images)

# Trạng thái trò chơi
game_state = None
last_game_state = None  # Lưu trạng thái trước để so sánh
lock = threading.Lock()
action_queue = queue.Queue()  # Hàng đợi cho hành động của client

def receive_data():
    global game_state, last_game_state
    while True:
        try:
            data = client.recv(4096).decode()
            with lock:
                new_state = ast.literal_eval(data)
                # Chỉ in nếu trạng thái thay đổi
                if last_game_state is None or \
                   new_state["players"] != last_game_state["players"] or \
                   new_state["bullets"] != last_game_state["bullets"]:
                    game_state = new_state
                    print(f"Received from server: Players={len(game_state['players'])}, Bullets={len(game_state['bullets'])}")
                    for pid, p in game_state["players"].items():
                        print(f"  Player {pid}: x={p['x']}, y={p['y']}, dir={p['dir']}, score={p['score']}")
                    last_game_state = copy.deepcopy(game_state)
        except:
            print("Disconnected from server")
            break

def send_actions():
    while True:
        try:
            # Lấy hành động từ hàng đợi
            action = action_queue.get(block=True, timeout=0.1)
            print(f"Dequeued action: {action}")
            client.send(action.encode())
            print(f"Sent to server: {action}")
            action_queue.task_done()
        except queue.Empty:
            pass

threading.Thread(target=receive_data, daemon=True).start()
threading.Thread(target=send_actions, daemon=True).start()

def main():
    running = True
    my_pid = f"{client.getsockname()[0]}:{client.getsockname()[1]}"
    print(f"Client started with ID: {my_pid}")
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                print("Client quitting (window closed)")
                running = False
            elif event.type == pygame.KEYDOWN:
                action = None
                if event.key == pygame.K_UP:
                    action = "up"
                elif event.key == pygame.K_DOWN:
                    action = "down"
                elif event.key == pygame.K_LEFT:
                    action = "left"
                elif event.key == pygame.K_RIGHT:
                    action = "right"
                elif event.key == pygame.K_SPACE:
                    action = "shoot"
                elif event.key == pygame.K_q:
                    print("Client quitting (Q pressed)")
                    running = False
                
                if action:
                    action_queue.put(action)
                    print(f"Enqueued action: {action}")

        # Vẽ giao diện
        screen.fill((255, 255, 255))
        with lock:
            if game_state:
                # Vẽ mê cung
                for y, row in enumerate(game_state["maze"]):
                    for x, cell in enumerate(row):
                        if cell == 1:
                            pygame.draw.rect(screen, (0, 0, 0), (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

                # Vẽ xe tăng
                my_pid = f"{client.getsockname()[0]}:{client.getsockname()[1]}"
                for pid, p in game_state["players"].items():
                    if pid == my_pid:
                        tank_img = my_tank_image
                    else:
                        random.seed(pid)
                        tank_img = random.choice(tank_images)
                    
                    if p["dir"] == "up":
                        rotated_img = pygame.transform.rotate(tank_img, 0)
                    elif p["dir"] == "down":
                        rotated_img = pygame.transform.rotate(tank_img, 180)
                    elif p["dir"] == "left":
                        rotated_img = pygame.transform.rotate(tank_img, 90)
                    elif p["dir"] == "right":
                        rotated_img = pygame.transform.rotate(tank_img, -90)
                    
                    screen.blit(rotated_img, (p["x"] * CELL_SIZE, p["y"] * CELL_SIZE))

                # Vẽ đạn
                for b in game_state["bullets"]:
                    pygame.draw.circle(screen, (255, 255, 0), (b["x"] * CELL_SIZE + CELL_SIZE // 2, b["y"] * CELL_SIZE + CELL_SIZE // 2), 5)

                # Vẽ bảng điểm
                font = pygame.font.SysFont(None, 30)
                y_offset = HEIGHT + 10
                for pid, p in game_state["players"].items():
                    text = font.render(f"Player {pid}: {p['score']}", True, (0, 0, 0))
                    screen.blit(text, (10, y_offset))
                    y_offset += 30

        pygame.display.flip()
        clock.tick(60)

    client.close()
    pygame.quit()

if __name__ == "__main__":
    main()