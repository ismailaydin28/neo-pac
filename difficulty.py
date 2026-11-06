"""Difficulty presets kept separate from game orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from diagnostics import get_feature_logger


@dataclass(frozen=True)
class DifficultyConfig:
    key: str
    label_tr: str
    label_en: str
    enemy_speed: float
    power_scale: float
    starting_lives: int
    ai_exploration_scale: float


DIFFICULTIES = (
    DifficultyConfig("casual", "Rahat", "Casual", 0.82, 1.30, 5, 1.25),
    DifficultyConfig("normal", "Normal", "Normal", 1.00, 1.00, 3, 1.00),
    DifficultyConfig("hard", "Zor", "Hard", 1.16, 0.82, 2, 0.72),
    DifficultyConfig("nightmare", "Siber Kâbus", "Cyber Nightmare", 1.30, 0.65, 1, 0.45),
)


class DifficultyManager:
    def __init__(self, selected="normal"):
        self.logger = get_feature_logger("difficulty")
        keys = [item.key for item in DIFFICULTIES]
        self.index = keys.index(selected) if selected in keys else 1

    @property
    def current(self):
        return DIFFICULTIES[self.index]

    def cycle(self, step=1):
        self.index = (self.index + step) % len(DIFFICULTIES)
        self.logger.info("Zorluk secildi | zorluk=%s", self.current.key)
        return self.current

    def label(self, language="tr"):
        return self.current.label_tr if language == "tr" else self.current.label_en
