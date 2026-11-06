"""All collectible abilities and their independent timers."""

from __future__ import annotations

from dataclasses import dataclass
import random

from diagnostics import get_feature_logger


@dataclass(frozen=True)
class PowerUpDefinition:
    key: str
    label_tr: str
    label_en: str
    color: tuple
    duration: int


POWERUPS = (
    PowerUpDefinition("overclock", "Aşırı Güç", "Overclock", (255, 60, 220), 480),
    PowerUpDefinition("shield", "Kalkan", "Shield", (80, 210, 255), 0),
    PowerUpDefinition("freeze", "Zaman Dondurma", "Time Freeze", (120, 230, 255), 240),
    PowerUpDefinition("magnet", "Enerji Mıknatısı", "Energy Magnet", (255, 210, 60), 360),
    PowerUpDefinition("decoy", "Sahte Oyuncu", "Decoy", (180, 100, 255), 300),
    PowerUpDefinition("chain_dash", "Zincir Dash", "Chain Dash", (80, 255, 170), 360),
)

POWERUP_BY_KEY = {item.key: item for item in POWERUPS}


def assign_powerups(seed, positions):
    """Deterministically distribute distinct powers across a maze."""
    rng = random.Random(seed ^ 0x5EEDC0DE)
    choices = [item.key for item in POWERUPS]
    rng.shuffle(choices)
    return {position: choices[index % len(choices)]
            for index, position in enumerate(sorted(positions))}


class PowerUpManager:
    def __init__(self):
        self.logger = get_feature_logger("powerups")
        self.reset()

    def reset(self):
        self.timers = {item.key: 0 for item in POWERUPS}
        self.shield_hits = 0
        self.decoy_tile = None
        self.last_activated = None

    def assign_for_maze(self, seed, positions):
        return assign_powerups(seed, positions)

    def activate(self, key, player_tile=None, duration_scale=1.0):
        definition = POWERUP_BY_KEY.get(key, POWERUP_BY_KEY["overclock"])
        self.last_activated = definition.key
        if definition.key == "shield":
            self.shield_hits = min(2, self.shield_hits + 1)
        else:
            self.timers[definition.key] = max(
                self.timers[definition.key],
                max(1, int(definition.duration * duration_scale)),
            )
        if definition.key == "decoy":
            self.decoy_tile = player_tile
        self.logger.info("Guc etkin | tur=%s sure=%d kalkan=%d",
                         definition.key, self.timers[definition.key], self.shield_hits)
        return definition

    def update(self):
        ended = []
        for key, value in tuple(self.timers.items()):
            if value > 0:
                self.timers[key] -= 1
                if self.timers[key] == 0:
                    ended.append(key)
                    self.logger.info("Guc sona erdi | tur=%s", key)
        if "decoy" in ended:
            self.decoy_tile = None
        return ended

    def active(self, key):
        return self.timers.get(key, 0) > 0

    def consume_shield(self):
        if self.shield_hits <= 0:
            return False
        self.shield_hits -= 1
        self.logger.info("Kalkan darbeyi engelledi | kalan=%d", self.shield_hits)
        return True

    def remaining(self, key):
        return self.timers.get(key, 0)

    def label(self, language="tr"):
        definition = POWERUP_BY_KEY.get(self.last_activated)
        if not definition:
            return ""
        return definition.label_tr if language == "tr" else definition.label_en
