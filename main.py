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
RUN_SPEED_MULTIPLIER = 1.8
GRENADE_SPEED = 260
BULLET_SPEED = 560
PLAYER_SIZE = 36
PLAYER_SPRITE_SIZE = 120
BULLET_SIZE = 8
GRENADE_SIZE = 22
SHOOT_COOLDOWN = 0.2
MAX_HP = 5
GRENADE_COUNT = 3
GRENADE_DAMAGE = 3
BULLET_DAMAGE = 1
GRENADE_AOE_RADIUS = 70
GRENADE_AOE_DURATION = 0.18
CONTROLLER_DEADZONE = 0.35
ASSETS_DIR = Path(__file__).resolve().parent / "assets"
SOLDIER_SPRITE_PATH = ASSETS_DIR / "soldier.png"


def generate_random_walls(arena: pygame.Rect) -> list[pygame.Rect]:
    wall_count = random.randint(13, 18)
    walls: list[pygame.Rect] = []

    p1_safe = pygame.Rect(0, arena.height // 2 - 90, 230, 180)
    p2_safe = pygame.Rect(arena.width - 230, arena.height // 2 - 90, 230, 180)
    center_lane = pygame.Rect(arena.width // 2 - 90, arena.height // 2 - 40, 180, 80)

    tries = 0
    while len(walls) < wall_count and tries < 520:
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

    loaded = pygame.image.load(str(SOLDIER_SPRITE_PATH))
    has_alpha = bool(loaded.get_flags() & pygame.SRCALPHA) or loaded.get_masks()[3] != 0

    if has_alpha:
        sprite = loaded.convert_alpha()
    else:
        # If there is no alpha channel, remove a white-ish backdrop via colorkey.
        corner = loaded.get_at((0, 0))[:3]
        corner_brightness = sum(corner)
        key_color = (255, 255, 255) if corner_brightness > 600 else corner
        sprite = loaded.convert()
        sprite.set_colorkey(key_color, pygame.RLEACCEL)

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


def reset_player_positions(players: dict[str, dict[str, object]], arena: pygame.Rect) -> None:
    players["p1"]["rect"].topleft = (120, arena.height // 2 - PLAYER_SIZE // 2)
    players["p2"]["rect"].topleft = (arena.width - 120 - PLAYER_SIZE, arena.height // 2 - PLAYER_SIZE // 2)


def create_display(fullscreen: bool, windowed_size: tuple[int, int]) -> pygame.Surface:
    if fullscreen:
        return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    return pygame.display.set_mode(windowed_size, pygame.RESIZABLE)


def rect_within_radius(rect: pygame.Rect, center: pygame.Vector2, radius: float) -> bool:
    closest_x = max(rect.left, min(center.x, rect.right))
    closest_y = max(rect.top, min(center.y, rect.bottom))
    dx = center.x - closest_x
    dy = center.y - closest_y
    return dx * dx + dy * dy <= radius * radius


def draw_grenade_projectile(screen: pygame.Surface, grenade_rect: pygame.Rect, velocity: pygame.Vector2) -> None:
    center = grenade_rect.center
    radius = max(4, grenade_rect.width // 2)

    # Main body with a small highlight to feel round instead of boxy.
    pygame.draw.circle(screen, (84, 74, 63), center, radius)
    pygame.draw.circle(screen, (120, 107, 92), (center[0] - 2, center[1] - 2), max(2, radius // 2))
    pygame.draw.circle(screen, (28, 25, 23), center, radius, 1)

    # Fuse cap and short fuse line pointing opposite to travel direction.
    direction = pygame.Vector2(velocity)
    if direction.length_squared() > 0:
        direction = direction.normalize()
    else:
        direction = pygame.Vector2(1, 0)
    fuse_start = (int(center[0] - direction.x * radius), int(center[1] - direction.y * radius))
    fuse_end = (int(fuse_start[0] - direction.x * 6), int(fuse_start[1] - direction.y * 6))
    pygame.draw.circle(screen, (199, 210, 254), fuse_start, 2)
    pygame.draw.line(screen, (244, 114, 182), fuse_start, fuse_end, 2)


def apply_deadzone(value: float, deadzone: float) -> float:
    if abs(value) < deadzone:
        return 0.0
    return value


def get_controller_intent(controller: "pygame.joystick.Joystick | None") -> tuple[float, float, bool, bool]:
    if controller is None:
        return 0.0, 0.0, False, False

    axis_x = apply_deadzone(controller.get_axis(0), CONTROLLER_DEADZONE) if controller.get_numaxes() > 0 else 0.0
    axis_y = apply_deadzone(controller.get_axis(1), CONTROLLER_DEADZONE) if controller.get_numaxes() > 1 else 0.0

    dpad_x = 0
    dpad_y = 0
    if controller.get_numhats() > 0:
        hat_x, hat_y = controller.get_hat(0)
        dpad_x = hat_x
        dpad_y = -hat_y

    x_input = float(dpad_x) if dpad_x != 0 else axis_x
    y_input = float(dpad_y) if dpad_y != 0 else axis_y

    button_count = controller.get_numbuttons()
    run = any(controller.get_button(i) for i in (4, 5) if i < button_count)
    fire = any(controller.get_button(i) for i in (0, 1, 2, 3) if i < button_count)
    return x_input, y_input, run, fire


def get_connected_controllers() -> list["pygame.joystick.Joystick"]:
    connected: list["pygame.joystick.Joystick"] = []
    for i in range(pygame.joystick.get_count()):
        joystick = pygame.joystick.Joystick(i)
        joystick.init()
        connected.append(joystick)
    return connected


def safe_get_events() -> list[pygame.event.Event]:
    try:
        return pygame.event.get()
    except (KeyError, SystemError):
        # Rare SDL/pygame event conversion glitch; keep running instead of crashing.
        pygame.event.pump()
        return []


def main() -> None:
    pygame.init()
    pygame.joystick.init()
    pygame.display.set_caption("Pygame - 2 Players")
    display_info = pygame.display.Info()
    windowed_size = (
        min(WIDTH, display_info.current_w),
        min(HEIGHT, display_info.current_h),
    )
    fullscreen = True
    screen = create_display(fullscreen, windowed_size)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 20)
    player_sprite = load_player_sprite(PLAYER_SPRITE_SIZE)
    controllers = get_connected_controllers()

    arena = screen.get_rect()
    grenade_max_range = arena.width / 3
    players = {
        "p1": {
            "rect": pygame.Rect(120, arena.height // 2 - PLAYER_SIZE // 2, PLAYER_SIZE, PLAYER_SIZE),
            "color": PLAYER1_COLOR,
            "hp": MAX_HP,
            "grenades": GRENADE_COUNT,
            "last_dir": pygame.Vector2(1, 0),
            "cooldown": 0.0,
        },
        "p2": {
            "rect": pygame.Rect(arena.width - 120 - PLAYER_SIZE, arena.height // 2 - PLAYER_SIZE // 2, PLAYER_SIZE, PLAYER_SIZE),
            "color": PLAYER2_COLOR,
            "hp": MAX_HP,
            "grenades": GRENADE_COUNT,
            "last_dir": pygame.Vector2(-1, 0),
            "cooldown": 0.0,
        },
    }

    walls = generate_random_walls(arena)

    bullets: list[dict[str, object]] = []
    explosions: list[dict[str, object]] = []

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in safe_get_events():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F11:
                    if not fullscreen:
                        windowed_size = screen.get_size()
                    fullscreen = not fullscreen
                    screen = create_display(fullscreen, windowed_size)
                    arena = screen.get_rect()
                    grenade_max_range = arena.width / 3
                    walls = generate_random_walls(arena)
                    reset_player_positions(players, arena)
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                windowed_size = (max(640, event.w), max(360, event.h))
                screen = create_display(False, windowed_size)
                arena = screen.get_rect()
                grenade_max_range = arena.width / 3
                walls = generate_random_walls(arena)
                reset_player_positions(players, arena)
            elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                controllers = get_connected_controllers()

        keys = pygame.key.get_pressed()

        p1_controller = controllers[0] if len(controllers) > 0 else None
        p2_controller = controllers[1] if len(controllers) > 1 else None

        p1_cx, p1_cy, p1_run_btn, p1_fire_btn = get_controller_intent(p1_controller)
        p2_cx, p2_cy, p2_run_btn, p2_fire_btn = get_controller_intent(p2_controller)

        p1_key_x = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        p1_key_y = int(keys[pygame.K_s]) - int(keys[pygame.K_w])
        p2_key_x = int(keys[pygame.K_RIGHT]) - int(keys[pygame.K_LEFT])
        p2_key_y = int(keys[pygame.K_DOWN]) - int(keys[pygame.K_UP])

        p1_x = p1_cx if p1_cx != 0 else float(p1_key_x)
        p1_y = p1_cy if p1_cy != 0 else float(p1_key_y)
        p2_x = p2_cx if p2_cx != 0 else float(p2_key_x)
        p2_y = p2_cy if p2_cy != 0 else float(p2_key_y)

        p1_run = keys[pygame.K_LSHIFT] or p1_run_btn
        p2_run = keys[pygame.K_RSHIFT] or p2_run_btn

        p1_speed = PLAYER_SPEED * (RUN_SPEED_MULTIPLIER if p1_run else 1.0)
        p2_speed = PLAYER_SPEED * (RUN_SPEED_MULTIPLIER if p2_run else 1.0)

        move_with_walls(
            players["p1"]["rect"],
            int(round(p1_x * p1_speed * dt)),
            int(round(p1_y * p1_speed * dt)),
            walls,
            arena,
        )
        move_with_walls(
            players["p2"]["rect"],
            int(round(p2_x * p2_speed * dt)),
            int(round(p2_y * p2_speed * dt)),
            walls,
            arena,
        )

        if p1_x != 0 or p1_y != 0:
            players["p1"]["last_dir"] = pygame.Vector2(p1_x, p1_y).normalize()
        if p2_x != 0 or p2_y != 0:
            players["p2"]["last_dir"] = pygame.Vector2(p2_x, p2_y).normalize()

        players["p1"]["cooldown"] = max(0.0, float(players["p1"]["cooldown"]) - dt)
        players["p2"]["cooldown"] = max(0.0, float(players["p2"]["cooldown"]) - dt)

        p1_fire = keys[pygame.K_SPACE] or p1_fire_btn
        p2_fire = keys[pygame.K_RCTRL] or p2_fire_btn

        if p1_fire and float(players["p1"]["cooldown"]) <= 0.0:
            direction = players["p1"]["last_dir"]
            origin = players["p1"]["rect"].center
            has_grenade = int(players["p1"]["grenades"]) > 0
            projectile_kind = "grenade" if has_grenade else "bullet"
            projectile_size = GRENADE_SIZE if has_grenade else BULLET_SIZE
            projectile_speed = GRENADE_SPEED if has_grenade else BULLET_SPEED
            bullets.append(
                {
                    "rect": pygame.Rect(
                        origin[0] - projectile_size // 2,
                        origin[1] - projectile_size // 2,
                        projectile_size,
                        projectile_size,
                    ),
                    "vel": pygame.Vector2(direction.x, direction.y) * projectile_speed,
                    "owner": "p1",
                    "kind": projectile_kind,
                    "distance": 0.0,
                }
            )
            players["p1"]["cooldown"] = SHOOT_COOLDOWN
            if has_grenade:
                players["p1"]["grenades"] = int(players["p1"]["grenades"]) - 1

        if p2_fire and float(players["p2"]["cooldown"]) <= 0.0:
            direction = players["p2"]["last_dir"]
            origin = players["p2"]["rect"].center
            has_grenade = int(players["p2"]["grenades"]) > 0
            projectile_kind = "grenade" if has_grenade else "bullet"
            projectile_size = GRENADE_SIZE if has_grenade else BULLET_SIZE
            projectile_speed = GRENADE_SPEED if has_grenade else BULLET_SPEED
            bullets.append(
                {
                    "rect": pygame.Rect(
                        origin[0] - projectile_size // 2,
                        origin[1] - projectile_size // 2,
                        projectile_size,
                        projectile_size,
                    ),
                    "vel": pygame.Vector2(direction.x, direction.y) * projectile_speed,
                    "owner": "p2",
                    "kind": projectile_kind,
                    "distance": 0.0,
                }
            )
            players["p2"]["cooldown"] = SHOOT_COOLDOWN
            if has_grenade:
                players["p2"]["grenades"] = int(players["p2"]["grenades"]) - 1

        kept_bullets: list[dict[str, object]] = []
        for bullet in bullets:
            bullet_rect = bullet["rect"]
            velocity = bullet["vel"]
            kind = bullet["kind"]
            travel_step = float(velocity.length() * dt)
            bullet["distance"] = float(bullet["distance"]) + travel_step
            bullet_rect.x += int(velocity.x * dt)
            bullet_rect.y += int(velocity.y * dt)

            hit_wall = any(bullet_rect.colliderect(wall) for wall in walls)
            out_of_bounds = not arena.colliderect(bullet_rect)
            reached_max_range = kind == "grenade" and float(bullet["distance"]) >= grenade_max_range

            owner = bullet["owner"]
            target = "p2" if owner == "p1" else "p1"
            hit_player = bullet_rect.colliderect(players[target]["rect"])

            if kind == "grenade" and (hit_wall or hit_player or out_of_bounds or reached_max_range):
                explosion_center = pygame.Vector2(bullet_rect.center)
                explosions.append({"center": explosion_center, "ttl": GRENADE_AOE_DURATION})

                for player_key in ("p1", "p2"):
                    if rect_within_radius(players[player_key]["rect"], explosion_center, GRENADE_AOE_RADIUS):
                        players[player_key]["hp"] = max(0, int(players[player_key]["hp"]) - GRENADE_DAMAGE)
                continue

            if kind == "bullet":
                if hit_wall or out_of_bounds:
                    continue
                if hit_player:
                    players[target]["hp"] = max(0, int(players[target]["hp"]) - BULLET_DAMAGE)
                    continue

            kept_bullets.append(bullet)

        bullets = kept_bullets

        kept_explosions: list[dict[str, object]] = []
        for explosion in explosions:
            explosion["ttl"] = float(explosion["ttl"]) - dt
            if float(explosion["ttl"]) > 0:
                kept_explosions.append(explosion)
        explosions = kept_explosions

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
            if bullet["kind"] == "grenade":
                draw_grenade_projectile(screen, bullet["rect"], bullet["vel"])
            else:
                pygame.draw.rect(screen, BULLET_COLOR, bullet["rect"], border_radius=4)

        for explosion in explosions:
            alpha = int(130 * (float(explosion["ttl"]) / GRENADE_AOE_DURATION))
            aoe_surface = pygame.Surface((arena.width, arena.height), pygame.SRCALPHA)
            pygame.draw.circle(
                aoe_surface,
                (255, 0, 0, max(0, min(130, alpha))),
                (int(explosion["center"].x), int(explosion["center"].y)),
                GRENADE_AOE_RADIUS,
            )
            pygame.draw.circle(
                aoe_surface,
                (255, 90, 90, max(0, min(180, alpha + 30))),
                (int(explosion["center"].x), int(explosion["center"].y)),
                GRENADE_AOE_RADIUS,
                2,
            )
            screen.blit(aoe_surface, (0, 0))

        status_text = font.render(
            (
                f"P1 HP: {players['p1']['hp']} G: {players['p1']['grenades']}    "
                f"P2 HP: {players['p2']['hp']} G: {players['p2']['grenades']}    "
                f"FPS: {clock.get_fps():.1f}"
            ),
            True,
            TEXT_COLOR,
        )
        controls_text = font.render(
            "P1: WASD/Left Stick + Shift/LB run + Space/A fire | P2: Arrows/Stick + Shift/LB run + RCtrl/A fire",
            True,
            TEXT_COLOR,
        )
        controller_text = font.render(
            (
                f"Controllers: {len(controllers)} connected "
                f"(P1: {'Yes' if p1_controller else 'No'} | P2: {'Yes' if p2_controller else 'No'}) | F11: fullscreen"
            ),
            True,
            TEXT_COLOR,
        )
        screen.blit(status_text, (12, 10))
        screen.blit(controls_text, (12, 34))
        screen.blit(controller_text, (12, 58))

        pygame.display.flip()

    if winner is not None:
        end_screen = True
        while end_screen:
            for event in safe_get_events():
                if event.type == pygame.QUIT:
                    end_screen = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    end_screen = False

            screen.fill(BG_COLOR)
            msg = font.render(f"{winner} wins! Press ESC or close window.", True, (226, 232, 240))
            current_rect = screen.get_rect()
            screen.blit(
                msg,
                (
                    current_rect.width // 2 - msg.get_width() // 2,
                    current_rect.height // 2 - msg.get_height() // 2,
                ),
            )
            pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
