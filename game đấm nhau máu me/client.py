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
MAZE_WIDTH, MAZE_HEIGHT = 32, 16
WIDTH, HEIGHT = MAZE_WIDTH * CELL_SIZE, MAZE_HEIGHT * CELL_SIZE
UI_HEIGHT = 120
screen = pygame.display.set_mode((WIDTH, HEIGHT + UI_HEIGHT))
pygame.display.set_caption("Maze War")
clock = pygame.time.Clock()

# Tải font đẹp
try:
    font = pygame.font.Font("image/arial.ttf", 24)  # Giả sử có font trong thư mục image
except:
    font = pygame.font.SysFont("arial", 24)

# Màu sắc
BG_COLOR = (50, 50, 50)  # Xám đậm
WALL_COLOR = (100, 50, 0)  # Nâu gạch
BULLET_COLOR = (255, 200, 0)  # Vàng sáng
SCORE_BG_COLOR = (0, 100, 150)  # Xanh dương đậm
TEXT_COLOR = (255, 255, 255)  # Trắng

# Kết nối server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 5555))

# Tải tài nguyên
image_dir = "image"
sound_dir = "sound"

# Tải hình ảnh xe tăng
tank_images = {}
for filename in os.listdir(image_dir):
    if filename.startswith("tank-") and (filename.endswith(".png") or filename.endswith(".jpg")):
        name = filename.split(".")[0]  # Ví dụ: tank_red, tank_blue
        img = pygame.image.load(os.path.join(image_dir, filename))
        img = pygame.transform.scale(img, (CELL_SIZE, CELL_SIZE))
        tank_images[name] = img

if not tank_images:
    # Tạo hình mặc định nếu không có ảnh
    default_tank = pygame.Surface((CELL_SIZE, CELL_SIZE))
    default_tank.fill((0, 150, 0))
    tank_images["default"] = default_tank

# Tải hình tường
wall_image = None
try:
    wall_image = pygame.image.load(os.path.join(image_dir, "wall_brick.jpg"))
    wall_image = pygame.transform.scale(wall_image, (CELL_SIZE, CELL_SIZE))
except:
    wall_image = pygame.Surface((CELL_SIZE, CELL_SIZE))
    wall_image.fill(WALL_COLOR)

# Tải hình đạn
bullet_image = None
try:
    bullet_image = pygame.image.load(os.path.join(image_dir, "bullet.jpg"))
    bullet_image = pygame.transform.scale(bullet_image, (10, 10))
except:
    bullet_image = pygame.Surface((10, 10))
    bullet_image.fill(BULLET_COLOR)

# Tải âm thanh
try:
    pygame.mixer.init()
    shoot_sound = pygame.mixer.Sound(os.path.join(sound_dir, "shoot.mp3"))
    hit_sound = pygame.mixer.Sound(os.path.join(sound_dir, "hit.wav"))
except:
    shoot_sound = hit_sound = None

# Gán xe tăng cho client
my_tank_key = random.choice(list(tank_images.keys()))
my_tank_image = tank_images[my_tank_key]

# Trạng thái trò chơi
game_state = None
last_game_state = None
lock = threading.Lock()
action_queue = queue.Queue()
notifications = []  # Lưu thông báo tạm thời (pop-up)

# Hiệu ứng rung khi bắn
shake_frames = {}  # pid: frames còn lại
shake_duration = 5

def receive_data():
    global game_state, last_game_state
    while True:
        try:
            data = client.recv(4096).decode()
            with lock:
                new_state = ast.literal_eval(data)
                if last_game_state is None or \
                   new_state["players"] != last_game_state["players"] or \
                   new_state["bullets"] != last_game_state["bullets"]:
                    # Kiểm tra trúng đạn
                    if last_game_state and my_pid in new_state["players"]:
                        old_score = last_game_state["players"].get(my_pid, {}).get("score", 0)
                        new_score = new_state["players"][my_pid]["score"]
                        if new_score < old_score and new_score <= old_score - 5:
                            notifications.append(("Hit! -5", 120))  # Hiện 2 giây
                            if hit_sound:
                                hit_sound.play()
                    game_state = new_state
                    print(f"Received from server: Players={len(game_state['players'])}, Bullets={len(game_state['bullets'])}")
                    last_game_state = copy.deepcopy(game_state)
        except (ConnectionResetError, ConnectionAbortedError, socket.error) as e:
            print(f"Disconnected from server: {e}")
            break
        except Exception as e:
            print(f"Error receiving data: {e}")
            break

def send_actions():
    while True:
        try:
            action = action_queue.get(block=True, timeout=0.1)
            print(f"Dequeued action: {action}")
            if action == "shoot":
                shake_frames[my_pid] = shake_duration
                if shoot_sound:
                    shoot_sound.play()
            client.send(action.encode())
            print(f"Sent to server: {action}")
            action_queue.task_done()
        except queue.Empty:
            pass
        except (ConnectionResetError, ConnectionAbortedError, socket.error) as e:
            print(f"Cannot send action, server disconnected: {e}")
            break
        except Exception as e:
            print(f"Error sending action: {e}")
            break

# Thread xử lý thông báo
def update_notifications():
    while True:
        with lock:
            for i, (text, frames) in enumerate(notifications[:]):
                notifications[i] = (text, frames - 1)
                if frames <= 0:
                    notifications.pop(i)
        pygame.time.wait(16)  # ~60 FPS

threading.Thread(target=receive_data, daemon=True).start()
threading.Thread(target=send_actions, daemon=True).start()
threading.Thread(target=update_notifications, daemon=True).start()

def main():
    global my_pid
    running = True
    my_pid = f"{client.getsockname()[0]}:{client.getsockname()[1]}"
    print(f"Client started with ID: {my_pid}")
    
    # Tải nền
    try:
        background = pygame.image.load(os.path.join(image_dir, "background.jpg"))
        background = pygame.transform.scale(background, (WIDTH, HEIGHT))
    except:
        background = pygame.Surface((WIDTH, HEIGHT))
        background.fill(BG_COLOR)

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
                    try:
                        action_queue.put(action, block=False)
                        print(f"Enqueued action: {action}")
                    except queue.Full:
                        print("Action queue full, dropping action")

        # Vẽ giao diện
        screen.blit(background, (0, 0))  # Vẽ nền

        with lock:
            if game_state:
                # Vẽ mê cung
                for y, row in enumerate(game_state["maze"]):
                    for x, cell in enumerate(row):
                        if cell == 1:
                            screen.blit(wall_image, (x * CELL_SIZE, y * CELL_SIZE))

                # Vẽ xe tăng
                for pid, p in game_state["players"].items():
                    if pid == my_pid:
                        tank_img = my_tank_image
                    else:
                        random.seed(pid)
                        tank_key = random.choice(list(tank_images.keys()))
                        tank_img = tank_images[tank_key]
                    
                    # Xoay và rung
                    angle = {"up": 0, "down": 180, "left": 90, "right": -90}[p["dir"]]
                    rotated_img = pygame.transform.rotate(tank_img, angle)
                    x, y = p["x"] * CELL_SIZE, p["y"] * CELL_SIZE
                    if pid in shake_frames and shake_frames[pid] > 0:
                        x += random.randint(-2, 2)
                        y += random.randint(-2, 2)
                        shake_frames[pid] -= 1
                    
                    screen.blit(rotated_img, (x, y))

                # Vẽ đạn
                for b in game_state["bullets"]:
                    screen.blit(bullet_image, (b["x"] * CELL_SIZE + CELL_SIZE // 2 - 5, b["y"] * CELL_SIZE + CELL_SIZE // 2 - 5))

                # Vẽ UI
                ui_rect = pygame.Rect(0, HEIGHT, WIDTH, UI_HEIGHT)
                pygame.draw.rect(screen, SCORE_BG_COLOR, ui_rect)
                pygame.draw.rect(screen, (255, 255, 255), ui_rect, 2)  # Viền trắng
                y_offset = HEIGHT + 10
                for pid, p in game_state["players"].items():
                    text = font.render(f"Player {pid[-5:]}: {p['score']}", True, TEXT_COLOR)
                    screen.blit(text, (10, y_offset))
                    # Thanh máu giả định (score đại diện sức mạnh)
                    health_width = min(max(p["score"], 0), 100) * 2
                    pygame.draw.rect(screen, (200, 0, 0), (150, y_offset + 8, health_width, 10))
                    pygame.draw.rect(screen, (255, 255, 255), (250, y_offset + 5, 500, 10), 1)
                    y_offset += 40

                # Vẽ thông báo
                for text, frames in notifications:
                    text_surf = font.render(text, True, (255, 50, 50))
                    screen.blit(text_surf, (WIDTH // 2 - text_surf.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()
        clock.tick(60)

    try:
        client.close()
    except:
        pass
    pygame.quit()

if __name__ == "__main__":
    main()