import pygame
import socket
import ast
import threading


# Khởi tạo Pygame
pygame.init()
CELL_SIZE = 30
WIDTH, HEIGHT = 32 * CELL_SIZE, 16 * CELL_SIZE
screen = pygame.display.set_mode((WIDTH, HEIGHT + 100))  # Thêm 100px cho bảng điểm
pygame.display.set_caption("Maze War")
clock = pygame.time.Clock()

# Kết nối server
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(("localhost", 5555))  # Thay "localhost" bằng IP server nếu cần

# Trạng thái trò chơi
game_state = None
lock = threading.Lock()

def receive_data():
    global game_state
    while True:
        data = client.recv(4096).decode()
        with lock:
            game_state = ast.literal_eval(data)

threading.Thread(target=receive_data, daemon=True).start()

def main():
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    client.send("up".encode())
                elif event.key == pygame.K_DOWN:
                    client.send("down".encode())
                elif event.key == pygame.K_LEFT:
                    client.send("left".encode())
                elif event.key == pygame.K_RIGHT:
                    client.send("right".encode())
                elif event.key == pygame.K_SPACE:
                    client.send("shoot".encode())
                elif event.key == pygame.K_q:
                    running = False

        # Vẽ giao diện
        screen.fill((255, 255, 255))
        with lock:
            if game_state:
                # Vẽ mê cung
                for y, row in enumerate(game_state["maze"]):
                    for x, cell in enumerate(row):
                        if cell == 1:
                            pygame.draw.rect(screen, (0, 0, 0), (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))

                # Vẽ chiến binh
                for pid, p in game_state["players"].items():
                    color = (255, 0, 0) if pid == f"{client.getsockname()[0]}:{client.getsockname()[1]}" else (0, 0, 255)
                    pygame.draw.rect(screen, color, (p["x"] * CELL_SIZE, p["y"] * CELL_SIZE, CELL_SIZE, CELL_SIZE))

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
        clock.tick(10)  # Tốc độ di chuyển chiến binh

    client.close()
    pygame.quit()

if __name__ == "__main__":
    main()