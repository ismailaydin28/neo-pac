"""Keyboard, controller and mouse friendly tab state for the main menu."""

from __future__ import annotations

from diagnostics import get_feature_logger


TAB_KEYS = ("play", "game", "display", "controls", "stats")

TAB_OPTIONS = {
    "play": ("start", "daily_start", "quit"),
    "game": ("mode", "difficulty", "power_labels"),
    "display": ("accessibility", "fullscreen", "language", "diagnostics"),
    "controls": ("control_layout", "audio", "mouse_status"),
    "stats": ("high_score", "games_played", "highest_level",
              "dots_collected", "sentinels_eaten", "total_score"),
}


class MenuController:
    """Own only navigation state; game actions remain in the game controller."""

    def __init__(self):
        self.logger = get_feature_logger("menu")
        self.tab_index = 0
        self.selection_by_tab = {key: 0 for key in TAB_KEYS}

    @property
    def tab_key(self):
        return TAB_KEYS[self.tab_index]

    @property
    def options(self):
        return TAB_OPTIONS[self.tab_key]

    @property
    def selected_index(self):
        return self.selection_by_tab[self.tab_key]

    @property
    def selected_key(self):
        options = self.options
        if not options:
            return None
        return options[self.selected_index]

    def move_tab(self, step):
        self.tab_index = (self.tab_index + step) % len(TAB_KEYS)
        self._clamp_selection()
        self.logger.info("Menu sekmesi | sekme=%s", self.tab_key)
        return self.tab_key

    def select_tab(self, index):
        self.tab_index = max(0, min(len(TAB_KEYS) - 1, int(index)))
        self._clamp_selection()
        return self.tab_key

    def move_item(self, step):
        options = self.options
        if options:
            self.selection_by_tab[self.tab_key] = (
                self.selected_index + step
            ) % len(options)
        return self.selected_key

    def select_item(self, index):
        options = self.options
        if options:
            self.selection_by_tab[self.tab_key] = max(
                0, min(len(options) - 1, int(index))
            )
        return self.selected_key

    def _clamp_selection(self):
        options = self.options
        maximum = max(0, len(options) - 1)
        self.selection_by_tab[self.tab_key] = min(
            self.selection_by_tab[self.tab_key], maximum
        )
