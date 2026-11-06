"""Tests for tab navigation, mouse settings and visible power labels."""

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game import Game, GameState
from menu_system import MenuController, TAB_KEYS
from settings import SCREEN_H, SCREEN_W


class MenuSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["NEOPAC_PROFILE_PATH"] = os.path.join(
            self.tempdir.name, "profile.json"
        )
        self.game = Game(pygame.display.get_surface())
        self.game.state = GameState.MENU

    def tearDown(self):
        self.tempdir.cleanup()

    def _draw_menu(self):
        self.game.menu_screen.draw(
            self.game.screen,
            TAB_KEYS,
            self.game.menu_controller.tab_index,
            self.game.menu_controller.selected_index,
            self.game._menu_rows(),
        )

    def test_controller_wraps_tabs_and_rows(self):
        controller = MenuController()
        controller.move_tab(-1)
        self.assertEqual("stats", controller.tab_key)
        controller.move_item(-1)
        self.assertEqual("total_score", controller.selected_key)

    def test_wasd_changes_selection_and_setting(self):
        self.game.menu_controller.select_tab(1)  # game
        old_mode = self.game.game_modes.current.key
        self.game._handle_keydown(pygame.K_d)
        self.assertNotEqual(old_mode, self.game.game_modes.current.key)
        self.game._handle_keydown(pygame.K_s)
        self.assertEqual("difficulty", self.game.menu_controller.selected_key)

    def test_mouse_selects_tab_and_clicks_setting(self):
        self._draw_menu()
        game_tab = self.game.menu_screen.tab_rects[1].center
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                   button=1, pos=game_tab)
        self.game._handle_mouse_event(event)
        self.assertEqual("game", self.game.menu_controller.tab_key)

        self._draw_menu()
        old_mode = self.game.game_modes.current.key
        mode_row = self.game.menu_screen.row_rects[0].center
        event = pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                                   button=1, pos=mode_row)
        self.game._handle_mouse_event(event)
        self.assertNotEqual(old_mode, self.game.game_modes.current.key)

    def test_every_power_name_gets_a_label_surface(self):
        self.game.maze.show_power_labels = True
        self.game.maze.draw(self.game.screen)
        label_keys = {key for _language, key in self.game.maze._power_label_cache}
        self.assertEqual(set(self.game.maze.power_kinds.values()), label_keys)


if __name__ == "__main__":
    unittest.main()
