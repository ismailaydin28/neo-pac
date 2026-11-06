"""Fault-tolerant audio facade separated from the game state machine."""

from __future__ import annotations

import pygame

from diagnostics import get_feature_logger
from pellets import create_bgm_channel, create_sounds


class AudioManager:
    def __init__(self, muted=False):
        self.logger = get_feature_logger("audio")
        self.muted = bool(muted)
        self.available = False
        self.sounds = {}
        self.bgm_channel = None
        self._initialise()

    def _initialise(self):
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(44100, -16, 1, 512)
            self.sounds = create_sounds()
            self.bgm_channel = create_bgm_channel()
            self.available = True
            self._apply_volume()
            self.logger.info("Ses sistemi hazir | sessiz=%s", self.muted)
        except pygame.error as exc:
            self.available = False
            self.sounds = {}
            self.bgm_channel = None
            self.logger.warning("Ses sistemi kullanilamiyor | hata=%s", exc)

    def _apply_volume(self):
        if self.bgm_channel:
            self.bgm_channel.set_volume(0.0 if self.muted else 0.3)

    def toggle(self):
        self.muted = not self.muted
        self._apply_volume()
        self.logger.info("Ses durumu degisti | sessiz=%s", self.muted)
        return self.muted

    def play(self, name):
        if self.muted or not self.available:
            return False
        sound = self.sounds.get(name)
        if not sound:
            return False
        try:
            sound.play()
            return True
        except pygame.error as exc:
            self.logger.warning("Ses oynatilamadi | ad=%s hata=%s", name, exc)
            return False
