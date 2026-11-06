import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from game import Game, GameState
from game_modes import GameModeManager
from powerups import POWERUP_BY_KEY


class GameFeatureIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        pygame.display.set_mode((672, 804))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        os.environ["NEOPAC_PROFILE_PATH"] = os.path.join(
            self.tempdir.name, "profile.json"
        )
        self.game = Game(pygame.display.get_surface())
        self.game._full_reset()
        self.game.state = GameState.PLAYING

    def tearDown(self):
        self.tempdir.cleanup()

    def test_all_six_powers_are_present_and_activate_in_game(self):
        self.assertEqual(set(POWERUP_BY_KEY), set(self.game.maze.power_kinds.values()))
        for key in POWERUP_BY_KEY:
            self.game._activate_powerup(key, int(self.game.player.x), int(self.game.player.y))
        self.assertGreater(self.game.power_timer, 0)
        self.assertGreater(self.game.powerups.shield_hits, 0)
        for key in ("freeze", "magnet", "decoy", "chain_dash"):
            self.assertTrue(self.game.powerups.active(key), key)

    def test_no_dash_time_attack_and_endless_rules_reach_game_loop(self):
        self.game.game_modes = GameModeManager("no_dash")
        self.game.player.dir_x = 1
        self.game._handle_keydown(pygame.K_SPACE)
        self.assertEqual(0, self.game.player.dash_frames_left)

        self.game.game_modes = GameModeManager("time_attack")
        self.game.game_modes.frames_remaining = 1
        self.game._update_playing()
        self.assertEqual(GameState.GAME_OVER, self.game.state)

        self.game = Game(pygame.display.get_surface())
        self.game.game_modes = GameModeManager("endless")
        self.game._full_reset()
        self.game.state = GameState.PLAYING
        self.game.player.invincible_frames = 999
        for r, row in enumerate(self.game.maze.tiles):
            for c, tile in enumerate(row):
                if tile in (self.game.maze.DOT, self.game.maze.POWER):
                    self.game.maze.tiles[r][c] = self.game.maze.EMPTY
        self.game.maze.dots_remaining = 0
        self.game._update_playing()
        self.assertEqual(2, self.game.level)
        self.assertEqual(GameState.PLAYING, self.game.state)


if __name__ == "__main__":
    unittest.main()
