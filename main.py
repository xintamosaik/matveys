from __future__ import annotations

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
BULLET_SPEED = 750
PLAYER_SIZE = 36
PLAYER_SPRITE_SIZE = 120
BULLET_SIZE = 8
GRENADE_SIZE = 22
SHOOT_COOLDOWN = 0.2
MAX_HP = 5
EXPLOSIVE_GRENADE_COUNT = 2
SMOKE_GRENADE_COUNT = 2
SMOKE_REFILL_TIME = 20.0
BULLET_DAMAGE = 1
EXPLOSIVE_GRENADE_DAMAGE = 3
EXPLOSIVE_GRENADE_AOE_RADIUS = 70
EXPLOSIVE_GRENADE_AOE_DURATION = 0.18
SMOKE_AOE_RADIUS = 145
SMOKE_AOE_DURATION = 7.0
GRENADE_PICKUP_SIZE = 20
GRENADE_PICKUP_LIFETIME = 10.0
GRENADE_PICKUP_MIN_SPAWN = 5.0
GRENADE_PICKUP_MAX_SPAWN = 9.0
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


def spawn_grenade_pickup(arena: pygame.Rect, walls: list[pygame.Rect], players: dict[str, dict[str, object]]) -> pygame.Rect | None:
    for _ in range(120):
        x = random.randint(20, max(20, arena.width - GRENADE_PICKUP_SIZE - 20))
        y = random.randint(20, max(20, arena.height - GRENADE_PICKUP_SIZE - 20))
        candidate = pygame.Rect(x, y, GRENADE_PICKUP_SIZE, GRENADE_PICKUP_SIZE)

        if any(candidate.colliderect(wall) for wall in walls):
            continue
        if any(candidate.colliderect(players[key]["rect"]) for key in ("p1", "p2")):
            continue
        return candidate

    return None


def apply_deadzone(value: float, deadzone: float) -> float:
    if abs(value) < deadzone:
        return 0.0
    return value


def get_controller_intent(controller: "pygame.joystick.Joystick | None") -> tuple[float, float, bool, bool, bool, bool]:
    if controller is None:
        return 0.0, 0.0, False, False, False, False

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
    bullet_fire = button_count > 0 and bool(controller.get_button(0))
    grenade_fire = button_count > 1 and bool(controller.get_button(1))
    smoke_fire = button_count > 2 and bool(controller.get_button(2))
    return x_input, y_input, run, bullet_fire, grenade_fire, smoke_fire


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
    # Initialize only modules we use; pygame.init() can stall on audio backends.
    pygame.display.init()
    pygame.font.init()
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
    # Default pygame font avoids slow system font scanning at startup.
    font = pygame.font.Font(None, 28)
    player_sprite = load_player_sprite(PLAYER_SPRITE_SIZE)
    controllers = get_connected_controllers()

    arena = screen.get_rect()
    grenade_max_range = arena.width / 8
    players = {
        "p1": {
            "rect": pygame.Rect(120, arena.height // 2 - PLAYER_SIZE // 2, PLAYER_SIZE, PLAYER_SIZE),
            "color": PLAYER1_COLOR,
            "hp": MAX_HP,
            "grenades": EXPLOSIVE_GRENADE_COUNT,
            "smokes": SMOKE_GRENADE_COUNT,
            "smoke_refill": SMOKE_REFILL_TIME,
            "last_dir": pygame.Vector2(1, 0),
            "cooldown": 0.0,
        },
        "p2": {
            "rect": pygame.Rect(arena.width - 120 - PLAYER_SIZE, arena.height // 2 - PLAYER_SIZE // 2, PLAYER_SIZE, PLAYER_SIZE),
            "color": PLAYER2_COLOR,
            "hp": MAX_HP,
            "grenades": EXPLOSIVE_GRENADE_COUNT,
            "smokes": SMOKE_GRENADE_COUNT,
            "smoke_refill": SMOKE_REFILL_TIME,
            "last_dir": pygame.Vector2(-1, 0),
            "cooldown": 0.0,
        },
    }

    walls = generate_random_walls(arena)

    bullets: list[dict[str, object]] = []
    smoke_clouds: list[dict[str, object]] = []
    blast_effects: list[dict[str, object]] = []
    grenade_pickups: list[dict[str, object]] = []
    pickup_spawn_timer = random.uniform(GRENADE_PICKUP_MIN_SPAWN, GRENADE_PICKUP_MAX_SPAWN)

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
                    grenade_max_range = arena.width / 8
                    walls = generate_random_walls(arena)
                    reset_player_positions(players, arena)
                    grenade_pickups.clear()
                    pickup_spawn_timer = random.uniform(GRENADE_PICKUP_MIN_SPAWN, GRENADE_PICKUP_MAX_SPAWN)
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                windowed_size = (max(640, event.w), max(360, event.h))
                screen = create_display(False, windowed_size)
                arena = screen.get_rect()
                grenade_max_range = arena.width / 8
                walls = generate_random_walls(arena)
                reset_player_positions(players, arena)
                grenade_pickups.clear()
                pickup_spawn_timer = random.uniform(GRENADE_PICKUP_MIN_SPAWN, GRENADE_PICKUP_MAX_SPAWN)
            elif event.type in (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED):
                controllers = get_connected_controllers()

        keys = pygame.key.get_pressed()

        p1_controller = controllers[0] if len(controllers) > 0 else None
        p2_controller = controllers[1] if len(controllers) > 1 else None

        p1_cx, p1_cy, p1_run_btn, p1_bullet_btn, p1_grenade_btn, p1_smoke_btn = get_controller_intent(p1_controller)
        p2_cx, p2_cy, p2_run_btn, p2_bullet_btn, p2_grenade_btn, p2_smoke_btn = get_controller_intent(p2_controller)

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

        for player_key in ("p1", "p2"):
            player_smokes = int(players[player_key]["smokes"])
            if player_smokes >= SMOKE_GRENADE_COUNT:
                players[player_key]["smoke_refill"] = SMOKE_REFILL_TIME
                continue
            players[player_key]["smoke_refill"] = max(0.0, float(players[player_key]["smoke_refill"]) - dt)
            if float(players[player_key]["smoke_refill"]) <= 0.0:
                players[player_key]["smokes"] = min(SMOKE_GRENADE_COUNT, player_smokes + 1)
                players[player_key]["smoke_refill"] = SMOKE_REFILL_TIME

        p1_bullet_fire = keys[pygame.K_SPACE] or p1_bullet_btn
        p1_grenade_fire = keys[pygame.K_q] or p1_grenade_btn
        p1_smoke_fire = keys[pygame.K_e] or p1_smoke_btn
        p2_bullet_fire = keys[pygame.K_RCTRL] or p2_bullet_btn
        p2_grenade_fire = keys[pygame.K_PERIOD] or p2_grenade_btn
        p2_smoke_fire = keys[pygame.K_COMMA] or p2_smoke_btn

        def spawn_projectile(player_key: str, projectile_kind: str) -> None:
            direction = players[player_key]["last_dir"]
            origin = players[player_key]["rect"].center
            projectile_size = GRENADE_SIZE if projectile_kind in ("grenade", "smoke_grenade") else BULLET_SIZE
            projectile_speed = GRENADE_SPEED if projectile_kind in ("grenade", "smoke_grenade") else BULLET_SPEED
            bullets.append(
                {
                    "rect": pygame.Rect(
                        origin[0] - projectile_size // 2,
                        origin[1] - projectile_size // 2,
                        projectile_size,
                        projectile_size,
                    ),
                    "vel": pygame.Vector2(direction.x, direction.y) * projectile_speed,
                    "owner": player_key,
                    "kind": projectile_kind,
                    "distance": 0.0,
                }
            )
            players[player_key]["cooldown"] = SHOOT_COOLDOWN

        if float(players["p1"]["cooldown"]) <= 0.0:
            if p1_bullet_fire:
                spawn_projectile("p1", "bullet")
            elif p1_grenade_fire and int(players["p1"]["grenades"]) > 0:
                spawn_projectile("p1", "grenade")
                players["p1"]["grenades"] = int(players["p1"]["grenades"]) - 1
            elif p1_smoke_fire and int(players["p1"]["smokes"]) > 0:
                spawn_projectile("p1", "smoke_grenade")
                players["p1"]["smokes"] = int(players["p1"]["smokes"]) - 1

        if float(players["p2"]["cooldown"]) <= 0.0:
            if p2_bullet_fire:
                spawn_projectile("p2", "bullet")
            elif p2_grenade_fire and int(players["p2"]["grenades"]) > 0:
                spawn_projectile("p2", "grenade")
                players["p2"]["grenades"] = int(players["p2"]["grenades"]) - 1
            elif p2_smoke_fire and int(players["p2"]["smokes"]) > 0:
                spawn_projectile("p2", "smoke_grenade")
                players["p2"]["smokes"] = int(players["p2"]["smokes"]) - 1

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
            reached_max_range = kind in ("grenade", "smoke_grenade") and float(bullet["distance"]) >= grenade_max_range

            owner = bullet["owner"]
            target = "p2" if owner == "p1" else "p1"
            hit_player = bullet_rect.colliderect(players[target]["rect"])

            if kind == "smoke_grenade" and (hit_player or hit_wall or out_of_bounds or reached_max_range):
                smoke_center = pygame.Vector2(bullet_rect.center)
                smoke_clouds.append({"center": smoke_center, "ttl": SMOKE_AOE_DURATION})
                continue

            if kind == "grenade" and (hit_player or hit_wall or out_of_bounds or reached_max_range):
                blast_center = pygame.Vector2(bullet_rect.center)
                blast_effects.append({"center": blast_center, "ttl": EXPLOSIVE_GRENADE_AOE_DURATION})
                for player_key in ("p1", "p2"):
                    if rect_within_radius(players[player_key]["rect"], blast_center, EXPLOSIVE_GRENADE_AOE_RADIUS):
                        players[player_key]["hp"] = max(0, int(players[player_key]["hp"]) - EXPLOSIVE_GRENADE_DAMAGE)
                continue

            if kind == "bullet":
                if hit_wall or out_of_bounds:
                    continue
                target_hidden_in_smoke = any(
                    rect_within_radius(players[target]["rect"], cloud["center"], SMOKE_AOE_RADIUS) for cloud in smoke_clouds
                )
                if target_hidden_in_smoke:
                    continue
                if hit_player:
                    players[target]["hp"] = max(0, int(players[target]["hp"]) - BULLET_DAMAGE)
                    continue

            kept_bullets.append(bullet)

        bullets = kept_bullets

        kept_smoke_clouds: list[dict[str, object]] = []
        for smoke_cloud in smoke_clouds:
            smoke_cloud["ttl"] = float(smoke_cloud["ttl"]) - dt
            if float(smoke_cloud["ttl"]) > 0:
                kept_smoke_clouds.append(smoke_cloud)
        smoke_clouds = kept_smoke_clouds

        kept_blast_effects: list[dict[str, object]] = []
        for blast_effect in blast_effects:
            blast_effect["ttl"] = float(blast_effect["ttl"]) - dt
            if float(blast_effect["ttl"]) > 0:
                kept_blast_effects.append(blast_effect)
        blast_effects = kept_blast_effects

        pickup_spawn_timer -= dt
        if pickup_spawn_timer <= 0.0:
            pickup_spawn_timer = random.uniform(GRENADE_PICKUP_MIN_SPAWN, GRENADE_PICKUP_MAX_SPAWN)
            pickup_rect = spawn_grenade_pickup(arena, walls, players)
            if pickup_rect is not None:
                grenade_pickups.append({"rect": pickup_rect, "ttl": GRENADE_PICKUP_LIFETIME})

        kept_pickups: list[dict[str, object]] = []
        for pickup in grenade_pickups:
            pickup["ttl"] = float(pickup["ttl"]) - dt
            if float(pickup["ttl"]) <= 0.0:
                continue

            picked = False
            for player_key in ("p1", "p2"):
                if pickup["rect"].colliderect(players[player_key]["rect"]):
                    players[player_key]["grenades"] = EXPLOSIVE_GRENADE_COUNT
                    picked = True
                    break

            if not picked:
                kept_pickups.append(pickup)
        grenade_pickups = kept_pickups

        winner = None
        if int(players["p1"]["hp"]) <= 0:
            winner = "Player 2"
        elif int(players["p2"]["hp"]) <= 0:
            winner = "Player 1"

        if winner is not None:
            running = False

        hidden_players: dict[str, bool] = {
            key: any(rect_within_radius(players[key]["rect"], cloud["center"], SMOKE_AOE_RADIUS) for cloud in smoke_clouds)
            for key in ("p1", "p2")
        }

        screen.fill(BG_COLOR)
        for wall in walls:
            pygame.draw.rect(screen, WALL_COLOR, wall, border_radius=4)
        for key in ("p1", "p2"):
            if hidden_players[key]:
                continue
            if player_sprite is not None:
                draw_player_sprite(screen, player_sprite, players[key]["rect"], players[key]["last_dir"])
            else:
                pygame.draw.rect(screen, players[key]["color"], players[key]["rect"], border_radius=6)
        for bullet in bullets:
            if bullet["kind"] in ("grenade", "smoke_grenade"):
                draw_grenade_projectile(screen, bullet["rect"], bullet["vel"])
            else:
                pygame.draw.rect(screen, BULLET_COLOR, bullet["rect"], border_radius=4)

        for smoke_cloud in smoke_clouds:
            alpha = int(130 * (float(smoke_cloud["ttl"]) / SMOKE_AOE_DURATION))
            aoe_surface = pygame.Surface((arena.width, arena.height), pygame.SRCALPHA)
            pygame.draw.circle(
                aoe_surface,
                (110, 231, 183, max(0, min(145, alpha))),
                (int(smoke_cloud["center"].x), int(smoke_cloud["center"].y)),
                SMOKE_AOE_RADIUS,
            )
            pygame.draw.circle(
                aoe_surface,
                (52, 211, 153, max(0, min(190, alpha + 35))),
                (int(smoke_cloud["center"].x), int(smoke_cloud["center"].y)),
                SMOKE_AOE_RADIUS,
                2,
            )
            screen.blit(aoe_surface, (0, 0))

        for blast_effect in blast_effects:
            alpha = int(170 * (float(blast_effect["ttl"]) / EXPLOSIVE_GRENADE_AOE_DURATION))
            blast_surface = pygame.Surface((arena.width, arena.height), pygame.SRCALPHA)
            pygame.draw.circle(
                blast_surface,
                (255, 90, 90, max(0, min(170, alpha))),
                (int(blast_effect["center"].x), int(blast_effect["center"].y)),
                EXPLOSIVE_GRENADE_AOE_RADIUS,
            )
            pygame.draw.circle(
                blast_surface,
                (255, 170, 120, max(0, min(210, alpha + 35))),
                (int(blast_effect["center"].x), int(blast_effect["center"].y)),
                EXPLOSIVE_GRENADE_AOE_RADIUS,
                2,
            )
            screen.blit(blast_surface, (0, 0))

        for pickup in grenade_pickups:
            pickup_rect = pickup["rect"]
            center = pickup_rect.center
            radius = max(4, pickup_rect.width // 2)
            pygame.draw.circle(screen, (74, 222, 128), center, radius)
            pygame.draw.circle(screen, (22, 163, 74), center, radius, 2)
            pygame.draw.line(screen, (236, 253, 245), (center[0] - 4, center[1]), (center[0] + 4, center[1]), 2)
            pygame.draw.line(screen, (236, 253, 245), (center[0], center[1] - 4), (center[0], center[1] + 4), 2)

        status_text = font.render(
            (
                f"P1 HP: {players['p1']['hp']} G: {players['p1']['grenades']} S: {players['p1']['smokes']}    "
                f"P2 HP: {players['p2']['hp']} G: {players['p2']['grenades']} S: {players['p2']['smokes']}    "
                f"FPS: {clock.get_fps():.1f}"
            ),
            True,
            TEXT_COLOR,
        )
        controls_text = font.render(
            "P1: Space bullet, Q grenade, E smoke | P2: RCtrl bullet, . grenade, , smoke",
            True,
            TEXT_COLOR,
        )
        p1_refill_text = "Ready" if int(players["p1"]["smokes"]) >= SMOKE_GRENADE_COUNT else f"{float(players['p1']['smoke_refill']):.1f}s"
        p2_refill_text = "Ready" if int(players["p2"]["smokes"]) >= SMOKE_GRENADE_COUNT else f"{float(players['p2']['smoke_refill']):.1f}s"
        smoke_text = font.render(
            (
                f"Smoke refill: P1 {p1_refill_text} | P2 {p2_refill_text}  (Max {SMOKE_GRENADE_COUNT})"
            ),
            True,
            TEXT_COLOR,
        )
        controller_text = font.render(
            (
                f"Controllers: {len(controllers)} connected "
                f"(P1: {'Yes' if p1_controller else 'No'} | P2: {'Yes' if p2_controller else 'No'}) | A bullet, B grenade, X smoke | F11"
            ),
            True,
            TEXT_COLOR,
        )
        screen.blit(status_text, (12, 10))
        screen.blit(controls_text, (12, 34))
        screen.blit(smoke_text, (12, 58))
        screen.blit(controller_text, (12, 82))

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
