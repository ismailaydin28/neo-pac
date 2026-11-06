"""Accessibility presets and visible palette decisions."""

from __future__ import annotations

from dataclasses import dataclass

from diagnostics import get_feature_logger
from settings import ENEMY_COLORS


@dataclass(frozen=True)
class AccessibilityPreset:
    key: str
    label_tr: str
    label_en: str
    flash_strength: float
    scanlines: bool
    low_motion: bool
    screen_shake: bool
    enemy_colors: tuple


COLORBLIND_COLORS = (
    (230, 159, 0),
    (86, 180, 233),
    (0, 158, 115),
    (204, 121, 167),
)

PRESETS = (
    AccessibilityPreset("standard", "Standart", "Standard", 1.0, True, False, True, tuple(ENEMY_COLORS)),
    AccessibilityPreset("reduced_flash", "Az Parlama", "Reduced Flash", 0.25, True, False, True, tuple(ENEMY_COLORS)),
    AccessibilityPreset("colorblind", "Renk Körü", "Colorblind", 0.65, True, False, True, COLORBLIND_COLORS),
    AccessibilityPreset("low_motion", "Düşük Hareket", "Low Motion", 0.15, False, True, False, COLORBLIND_COLORS),
)


class AccessibilityManager:
    def __init__(self, selected="standard"):
        self.logger = get_feature_logger("accessibility")
        keys = [item.key for item in PRESETS]
        self.index = keys.index(selected) if selected in keys else 0

    @property
    def current(self):
        return PRESETS[self.index]

    def cycle(self, step=1):
        self.index = (self.index + step) % len(PRESETS)
        self.logger.info("Erisilebilirlik secildi | profil=%s", self.current.key)
        return self.current

    def enemy_color(self, index):
        colors = self.current.enemy_colors
        return colors[index % len(colors)]

    def label(self, language="tr"):
        return self.current.label_tr if language == "tr" else self.current.label_en
