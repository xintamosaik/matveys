import sys

import pygame


WIDTH, HEIGHT = 960, 540
BG_COLOR = (17, 24, 39)
PLAYER_COLOR = (240, 249, 255)
TEXT_COLOR = (148, 163, 184)
PLAYER_SPEED = 320


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Pygame Starter")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 20)

    player = pygame.Rect(WIDTH // 2 - 25, HEIGHT // 2 - 25, 50, 50)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        keys = pygame.key.get_pressed()
        move_x = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        move_y = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])

        player.x += int(move_x * PLAYER_SPEED * dt)
        player.y += int(move_y * PLAYER_SPEED * dt)

        player.clamp_ip(screen.get_rect())

        screen.fill(BG_COLOR)
        pygame.draw.rect(screen, PLAYER_COLOR, player, border_radius=8)

        fps_text = font.render(f"FPS: {clock.get_fps():.1f}", True, TEXT_COLOR)
        screen.blit(fps_text, (12, 10))

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
