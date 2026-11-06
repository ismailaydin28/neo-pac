"""Telegraphed personality abilities for the four Sentinel types."""

from __future__ import annotations

from diagnostics import get_feature_logger


ABILITY_NAMES = ("overdrive", "ambush_lock", "flank_boost", "cloak")


class SentinelAbility:
    def __init__(self, personality):
        self.personality = personality % 4
        self.name = ABILITY_NAMES[self.personality]
        self.logger = get_feature_logger("sentinel_abilities")
        self.tick = 0
        self.telegraph = False
        self.active = False
        self._last_active = False
        self.just_activated = False

    def reset(self):
        self.tick = 0
        self.telegraph = False
        self.active = False
        self._last_active = False
        self.just_activated = False

    def update(self, vulnerable=False):
        self.just_activated = False
        self.tick = (self.tick + 1) % 720
        if vulnerable:
            self.telegraph = False
            self.active = False
            return 1.0

        if self.personality == 0:
            self.telegraph = 480 <= self.tick < 540
            self.active = 540 <= self.tick < 660
            multiplier = 1.28 if self.active else 1.0
        elif self.personality == 1:
            self.telegraph = 300 <= self.tick < 360
            self.active = 360 <= self.tick < 480
            multiplier = 1.16 if self.active else 1.0
        elif self.personality == 2:
            self.telegraph = 180 <= self.tick < 240
            self.active = 240 <= self.tick < 330
            multiplier = 1.20 if self.active else 1.0
        else:
            self.telegraph = 420 <= self.tick < 480
            self.active = 480 <= self.tick < 600
            multiplier = 1.05 if self.active else 1.0

        if self.active and not self._last_active:
            self.just_activated = True
            self.logger.info("Sentinel yetenegi basladi | id=%d yetenek=%s",
                             self.personality, self.name)
        self._last_active = self.active
        return multiplier

    @property
    def visibility(self):
        return 0.38 if self.personality == 3 and self.active else 1.0
