import sys
import random
from pathlib import Path

import pygame


WIDTH, HEIGHT = 960, 540
BG_COLOR = (17, 24, 39)
PLAYER1_COLOR = (56, 189, 248)
PLAYER2_COLOR = (248, 113, 113)
WALL_COLOR = (55, 65, 81)
BULLET_COLOR = (250, 204, 21)
TEXT_COLOR = (148, 163, 184)
PLAYER_SPEED = 280
BULLET_SPEED = 560
PLAYER_SIZE = 36
BULLET_SIZE = 8
SHOOT_COOLDOWN = 0.2
MAX_HP = 5
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SOLDIER_SPRITE_PATH = ASSETS_DIR / "soldier.png"


def generate_random_walls(arena: pygame.Rect) -> list[pygame.Rect]:
    wall_count = random.randint(5, 8)
    walls: list[pygame.Rect] = []

    p1_safe = pygame.Rect(0, HEIGHT // 2 - 90, 230, 180)
    p2_safe = pygame.Rect(WIDTH - 230, HEIGHT // 2 - 90, 230, 180)
    center_lane = pygame.Rect(WIDTH // 2 - 90, HEIGHT // 2 - 40, 180, 80)

    tries = 0
    while len(walls) < wall_count and tries < 200:
        tries += 1

        if random.random() < 0.5:
            w = random.randint(50, 90)
            h = random.randint(120, 220)
        else:
            w = random.randint(120, 220)
            h = random.randint(50, 90)

        x = random.randint(40, arena.width - w - 40)
        y = random.randint(40, arena.height - h - 40)
        candidate = pygame.Rect(x, y, w, h)

        if candidate.colliderect(p1_safe) or candidate.colliderect(p2_safe):
            continue
        if candidate.colliderect(center_lane):
            continue
        if any(candidate.colliderect(wall.inflate(18, 18)) for wall in walls):
            continue

        walls.append(candidate)

    return walls


def move_with_walls(rect: pygame.Rect, dx: int, dy: int, walls: list[pygame.Rect], bounds: pygame.Rect) -> None:
    rect.x += dx
    for wall in walls:
        if rect.colliderect(wall):
            if dx > 0:
                rect.right = wall.left
            elif dx < 0:
                rect.left = wall.right

    rect.y += dy
    for wall in walls:
        if rect.colliderect(wall):
            if dy > 0:
                rect.bottom = wall.top
            elif dy < 0:
                rect.top = wall.bottom

    rect.clamp_ip(bounds)


def load_player_sprite(size: int) -> pygame.Surface | None:
    if not SOLDIER_SPRITE_PATH.exists():
        return None

    sprite = pygame.image.load(str(SOLDIER_SPRITE_PATH)).convert_alpha()
    return pygame.transform.smoothscale(sprite, (size, size))


def draw_player_sprite(
    screen: pygame.Surface,
    sprite: pygame.Surface,
    player_rect: pygame.Rect,
    direction: pygame.Vector2,
) -> None:
    # Rotate the sprite to face the player's latest movement/shoot direction.
    angle = -direction.as_polar()[1]
    rotated = pygame.transform.rotate(sprite, angle)
    rotated_rect = rotated.get_rect(center=player_rect.center)
    screen.blit(rotated, rotated_rect)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Pygame - 2 Players")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 20)
    player_sprite = load_player_sprite(PLAYER_SIZE)

    arena = screen.get_rect()
    players = {
        "p1": {
            "rect": pygame.Rect(120, HEIGHT // 2 - PLAYER_SIZE // 2, PLAYER_SIZE, PLAYER_SIZE),
            "color": PLAYER1_COLOR,
            "hp": MAX_HP,
            "last_dir": pygame.Vector2(1, 0),
            "cooldown": 0.0,
        },
        "p2": {
            "rect": pygame.Rect(WIDTH - 120 - PLAYER_SIZE, HEIGHT // 2 - PLAYER_SIZE // 2, PLAYER_SIZE, PLAYER_SIZE),
            "color": PLAYER2_COLOR,
            "hp": MAX_HP,
            "last_dir": pygame.Vector2(-1, 0),
            "cooldown": 0.0,
        },
    }

    walls = generate_random_walls(arena)

    bullets: list[dict[str, object]] = []

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()

        p1_x = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        p1_y = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
        p2_x = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        p2_y = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])

        move_with_walls(
            players["p1"]["rect"],
            int(p1_x * PLAYER_SPEED * dt),
            int(p1_y * PLAYER_SPEED * dt),
            walls,
            arena,
        )
        move_with_walls(
            players["p2"]["rect"],
            int(p2_x * PLAYER_SPEED * dt),
            int(p2_y * PLAYER_SPEED * dt),
            walls,
            arena,
        )

        if p1_x != 0 or p1_y != 0:
            players["p1"]["last_dir"] = pygame.Vector2(p1_x, p1_y).normalize()
        if p2_x != 0 or p2_y != 0:
            players["p2"]["last_dir"] = pygame.Vector2(p2_x, p2_y).normalize()

        players["p1"]["cooldown"] = max(0.0, float(players["p1"]["cooldown"]) - dt)
        players["p2"]["cooldown"] = max(0.0, float(players["p2"]["cooldown"]) - dt)

        if keys[pygame.K_SPACE] and float(players["p1"]["cooldown"]) <= 0.0:
            direction = players["p1"]["last_dir"]
            origin = players["p1"]["rect"].center
            bullets.append(
                {
                    "rect": pygame.Rect(origin[0] - BULLET_SIZE // 2, origin[1] - BULLET_SIZE // 2, BULLET_SIZE, BULLET_SIZE),
                    "vel": pygame.Vector2(direction.x, direction.y) * BULLET_SPEED,
                    "owner": "p1",
                }
            )
            players["p1"]["cooldown"] = SHOOT_COOLDOWN

        if keys[pygame.K_RCTRL] and float(players["p2"]["cooldown"]) <= 0.0:
            direction = players["p2"]["last_dir"]
            origin = players["p2"]["rect"].center
            bullets.append(
                {
                    "rect": pygame.Rect(origin[0] - BULLET_SIZE // 2, origin[1] - BULLET_SIZE // 2, BULLET_SIZE, BULLET_SIZE),
                    "vel": pygame.Vector2(direction.x, direction.y) * BULLET_SPEED,
                    "owner": "p2",
                }
            )
            players["p2"]["cooldown"] = SHOOT_COOLDOWN

        kept_bullets: list[dict[str, object]] = []
        for bullet in bullets:
            bullet_rect = bullet["rect"]
            velocity = bullet["vel"]
            bullet_rect.x += int(velocity.x * dt)
            bullet_rect.y += int(velocity.y * dt)

            if not arena.colliderect(bullet_rect):
                continue

            if any(bullet_rect.colliderect(wall) for wall in walls):
                continue

            owner = bullet["owner"]
            target = "p2" if owner == "p1" else "p1"
            if bullet_rect.colliderect(players[target]["rect"]):
                players[target]["hp"] = max(0, int(players[target]["hp"]) - 1)
                continue

            kept_bullets.append(bullet)

        bullets = kept_bullets

        winner = None
        if int(players["p1"]["hp"]) <= 0:
            winner = "Player 2"
        elif int(players["p2"]["hp"]) <= 0:
            winner = "Player 1"

        if winner is not None:
            running = False

        screen.fill(BG_COLOR)
        for wall in walls:
            pygame.draw.rect(screen, WALL_COLOR, wall, border_radius=4)
        for key in ("p1", "p2"):
            if player_sprite is not None:
                draw_player_sprite(screen, player_sprite, players[key]["rect"], players[key]["last_dir"])
            else:
                pygame.draw.rect(screen, players[key]["color"], players[key]["rect"], border_radius=6)
        for bullet in bullets:
            pygame.draw.rect(screen, BULLET_COLOR, bullet["rect"], border_radius=4)

        status_text = font.render(
            f"P1 HP: {players['p1']['hp']}    P2 HP: {players['p2']['hp']}    FPS: {clock.get_fps():.1f}",
            True,
            TEXT_COLOR,
        )
        controls_text = font.render("P1: WASD + SPACE | P2: ARROWS + RIGHT CTRL", True, TEXT_COLOR)
        screen.blit(status_text, (12, 10))
        screen.blit(controls_text, (12, 34))

        pygame.display.flip()

    if winner is not None:
        end_screen = True
        while end_screen:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    end_screen = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    end_screen = False

            screen.fill(BG_COLOR)
            msg = font.render(f"{winner} wins! Press ESC or close window.", True, (226, 232, 240))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - msg.get_height() // 2))
            pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
