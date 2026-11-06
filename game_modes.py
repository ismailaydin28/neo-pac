"""Independent rule sets for NeoPac game modes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from diagnostics import get_feature_logger


@dataclass(frozen=True)
class ModeConfig:
    key: str
    label_tr: str
    label_en: str
    time_limit_seconds: int | None = None
    one_life: bool = False
    dash_allowed: bool = True
    endless: bool = False
    daily_seed: bool = False


MODES = (
    ModeConfig("classic", "Klasik", "Classic"),
    ModeConfig("time_attack", "Süreye Karşı", "Time Attack", time_limit_seconds=120),
    ModeConfig("one_life", "Tek Can", "One Life", one_life=True),
    ModeConfig("no_dash", "Dash Yasak", "No Dash", dash_allowed=False),
    ModeConfig("daily", "Günlük Labirent", "Daily Maze", daily_seed=True),
    ModeConfig("endless", "Sonsuz", "Endless", endless=True),
)


class GameModeManager:
    def __init__(self, selected="classic"):
        self.logger = get_feature_logger("game_modes")
        keys = [item.key for item in MODES]
        self.index = keys.index(selected) if selected in keys else 0
        self.frames_remaining = None

    @property
    def current(self):
        return MODES[self.index]

    def cycle(self, step=1):
        self.index = (self.index + step) % len(MODES)
        self.logger.info("Oyun modu secildi | mod=%s", self.current.key)
        return self.current

    def select(self, key):
        for index, mode in enumerate(MODES):
            if mode.key == key:
                self.index = index
                self.logger.info("Oyun modu secildi | mod=%s", self.current.key)
                return self.current
        return self.current

    def begin_run(self, fps=60):
        limit = self.current.time_limit_seconds
        self.frames_remaining = None if limit is None else limit * fps
        self.logger.info("Oyun modu basladi | mod=%s sure=%s",
                         self.current.key, self.frames_remaining)

    def update(self):
        if self.frames_remaining is not None and self.frames_remaining > 0:
            self.frames_remaining -= 1
        return self.frames_remaining == 0

    def maze_seed(self, level, fallback=None, today=None):
        if not self.current.daily_seed:
            return fallback
        today = today or date.today()
        return int(today.strftime("%Y%m%d")) * 100 + int(level)

    @staticmethod
    def daily_key(today=None):
        return (today or date.today()).isoformat()

    def label(self, language="tr"):
        return self.current.label_tr if language == "tr" else self.current.label_en
