"""Rebindable keyboard layouts and generic gamepad input."""

from __future__ import annotations

import pygame

from diagnostics import get_feature_logger


LAYOUTS = (
    ("wasd_arrows", "WASD + Oklar", "WASD + Arrows",
     {"left": (pygame.K_a, pygame.K_LEFT), "right": (pygame.K_d, pygame.K_RIGHT),
      "up": (pygame.K_w, pygame.K_UP), "down": (pygame.K_s, pygame.K_DOWN)}),
    ("arrows", "Yalnız Oklar", "Arrows Only",
     {"left": (pygame.K_LEFT,), "right": (pygame.K_RIGHT,),
      "up": (pygame.K_UP,), "down": (pygame.K_DOWN,)}),
    ("ijkl", "IJKL", "IJKL",
     {"left": (pygame.K_j,), "right": (pygame.K_l,),
      "up": (pygame.K_i,), "down": (pygame.K_k,)}),
)


class ControlManager:
    def __init__(self, selected="wasd_arrows"):
        self.logger = get_feature_logger("controls")
        keys = [item[0] for item in LAYOUTS]
        self.index = keys.index(selected) if selected in keys else 0
        self.joysticks = []
        self.refresh_gamepads()

    @property
    def key(self):
        return LAYOUTS[self.index][0]

    def label(self, language="tr"):
        return LAYOUTS[self.index][1 if language == "tr" else 2]

    def cycle(self, step=1):
        self.index = (self.index + step) % len(LAYOUTS)
        self.logger.info("Kontrol duzeni secildi | duzen=%s", self.key)
        return self.key

    def refresh_gamepads(self):
        self.joysticks = []
        if not pygame.get_init():
            return
        try:
            pygame.joystick.init()
            for index in range(pygame.joystick.get_count()):
                joystick = pygame.joystick.Joystick(index)
                joystick.init()
                self.joysticks.append(joystick)
            self.logger.info("Oyun kollari tarandi | adet=%d", len(self.joysticks))
        except pygame.error as exc:
            self.logger.warning("Oyun kolu taranamadi | hata=%s", exc)

    def direction(self, keys):
        mapping = LAYOUTS[self.index][3]
        direction = (0, 0)
        if any(keys[key] for key in mapping["left"]): direction = (-1, 0)
        if any(keys[key] for key in mapping["right"]): direction = (1, 0)
        if any(keys[key] for key in mapping["up"]): direction = (0, -1)
        if any(keys[key] for key in mapping["down"]): direction = (0, 1)

        for joystick in self.joysticks:
            try:
                x = joystick.get_axis(0) if joystick.get_numaxes() > 0 else 0
                y = joystick.get_axis(1) if joystick.get_numaxes() > 1 else 0
                if abs(x) > 0.45 or abs(y) > 0.45:
                    direction = ((1 if x > 0 else -1), 0) if abs(x) > abs(y) \
                        else (0, (1 if y > 0 else -1))
                if joystick.get_numhats():
                    hx, hy = joystick.get_hat(0)
                    if hx: direction = (hx, 0)
                    if hy: direction = (0, -hy)
            except pygame.error:
                continue
        return direction

    @staticmethod
    def is_dash_event(event):
        return ((event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE)
                or (event.type == pygame.JOYBUTTONDOWN and event.button == 0))

    @staticmethod
    def is_pause_event(event):
        return ((event.type == pygame.KEYDOWN and event.key in (pygame.K_p, pygame.K_ESCAPE))
                or (event.type == pygame.JOYBUTTONDOWN and event.button in (6, 7)))
