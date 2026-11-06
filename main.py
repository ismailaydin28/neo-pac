# main.py — NeoPac Entry Point

import pygame
from settings import SCREEN_W, SCREEN_H
from diagnostics import configure_logging, LOG_FILE
from profile import ProfileStore
from localization import set_language, tr


def main():
    logger = configure_logging()
    logger.info("NeoPac baslatiliyor | log=%s", LOG_FILE)
    profile = ProfileStore()
    set_language(profile.setting("language", "tr"))
    # Configure audio before pygame initialises its subsystems.
    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()

    # Start with the largest comfortable portrait window. The game renders to
    # a fixed logical canvas and scales independently up to 4K/fullscreen.
    info = pygame.display.Info()
    scale = min(1.5, info.current_w * 0.82 / SCREEN_W,
                info.current_h * 0.88 / SCREEN_H)
    scale = max(0.75, scale)
    window_size = (int(SCREEN_W * scale), int(SCREEN_H * scale))
    saved_size = profile.setting("window_size")
    if (isinstance(saved_size, list) and len(saved_size) == 2
            and all(isinstance(value, int) and value > 0 for value in saved_size)):
        window_size = tuple(saved_size)
    flags = pygame.DOUBLEBUF | pygame.RESIZABLE
    if profile.setting("fullscreen", False):
        window_size = (SCREEN_W, SCREEN_H)
        flags = pygame.DOUBLEBUF | pygame.FULLSCREEN | pygame.SCALED
    try:
        screen = pygame.display.set_mode(window_size, flags, vsync=0)
    except Exception:
        if profile.setting("fullscreen", False):
            try:
                screen = pygame.display.set_mode(
                    (0, 0), pygame.DOUBLEBUF | pygame.FULLSCREEN, vsync=0
                )
            except Exception:
                screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        else:
            screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

    pygame.display.set_caption(tr("window_title"))
    pygame.display.set_icon(_make_icon())

    # Hide OS cursor (we don't need it in-game)
    pygame.mouse.set_visible(False)

    try:
        from game import Game
        game = Game(screen)
        game.run()
    except SystemExit:
        raise
    except Exception:
        logger.exception("Beklenmeyen oyun hatasi")
        raise
    finally:
        logger.info("NeoPac kapatildi")
        pygame.quit()


def _make_icon() -> pygame.Surface:
    """Generate a simple 32×32 neon-blue circle as the window icon."""
    icon = pygame.Surface((32, 32), pygame.SRCALPHA)
    icon.fill((0, 0, 0, 0))
    pygame.draw.circle(icon, (60, 180, 255), (16, 16), 12)
    pygame.draw.circle(icon, (200, 240, 255), (11, 11), 4)
    return icon


if __name__ == "__main__":
    main()
