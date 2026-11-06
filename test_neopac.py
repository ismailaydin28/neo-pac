"""Regression checks for procedural maps and core NeoPac systems."""

import os
import unittest
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("NEOPAC_PROFILE_PATH", "/tmp/neopac_test_profile.json")

import pygame

from localization import current_language, toggle_language, tr
from learning_ai import load_brains
from maze import Maze
from pellets import BGM_FILE
from player import Player
from settings import COLS, PORTAL_ROW
from game import Game, GameState
from enemy import Enemy
from settings import ENEMY_RESPAWN_FRAMES, POWER_DURATION


class NeoPacTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        pygame.display.set_mode((32, 32))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_generated_mazes_are_unique_and_completable(self):
        signatures = set()
        for seed in range(30):
            maze = Maze(seed=seed)
            queue = deque([maze.player_spawn])
            reachable = {maze.player_spawn}
            while queue:
                r, c = queue.popleft()
                for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    tile = (r + dr, c + dc)
                    if tile not in reachable and not maze.is_wall_at(*tile):
                        reachable.add(tile)
                        queue.append(tile)

            collectibles = {
                (r, c)
                for r, row in enumerate(maze.tiles)
                for c, tile in enumerate(row)
                if tile in (maze.DOT, maze.POWER)
            }
            self.assertLessEqual(collectibles, reachable)
            self.assertEqual(6, sum(tile == maze.POWER for row in maze.tiles for tile in row))
            self.assertEqual(6, len(set(maze.power_kinds.values())))
            self.assertEqual(maze.PORTAL, maze.tile_at(PORTAL_ROW, 0))
            self.assertEqual(maze.PORTAL, maze.tile_at(PORTAL_ROW, COLS - 1))
            signatures.add(tuple(tuple(row) for row in maze.tiles))

        self.assertEqual(30, len(signatures))

    def test_generated_spawns_are_open(self):
        maze = Maze(seed=42)
        Player(maze)
        self.assertFalse(maze.is_wall_at(*maze.player_spawn))
        self.assertTrue(all(not maze.is_wall_at(*tile) for tile in maze.enemy_spawns))

    def test_dash_into_wall_keeps_perpendicular_turn_available(self):
        """Regression: dash residue must not lock vertical movement."""
        maze = Maze(seed=0)
        player = Player(maze)
        player.tile_r, player.tile_c = 1, 24
        player.x, player.y = map(float, maze.tile_center(1, 24))
        player.dir_x, player.dir_y = 1, 0
        player.next_dir_x, player.next_dir_y = 1, 0
        self.assertTrue(player.request_dash())

        for _ in range(10):
            player.update()

        self.assertEqual(0, player.dash_frames_left)
        self.assertEqual(maze.tile_center(player.tile_r, player.tile_c),
                         (player.x, player.y))
        before_y = player.y
        player.next_dir_x, player.next_dir_y = 0, 1
        player.update()
        self.assertGreater(player.y, before_y)

    def test_turkish_is_default_and_language_can_toggle(self):
        while current_language() != "tr":
            toggle_language()
        self.assertEqual("PUAN", tr("score"))
        toggle_language()
        self.assertEqual("SCORE", tr("score"))
        toggle_language()

    def test_ogg_theme_is_packaged_and_readable(self):
        self.assertTrue(BGM_FILE.is_file())
        theme = pygame.mixer.Sound(str(BGM_FILE))
        self.assertAlmostEqual(16.0, theme.get_length(), delta=0.1)

    def test_pretrained_learning_brains_are_packaged(self):
        brains = load_brains()
        self.assertEqual(4, len(brains))
        self.assertTrue(all(brain.steps > 0 and brain.q for brain in brains))

    def test_pause_menu_restart_and_main_menu_actions(self):
        screen = pygame.display.get_surface()
        game = Game(screen)
        game.state = GameState.PLAYING
        game._handle_keydown(pygame.K_p)
        self.assertEqual(GameState.PAUSED, game.state)

        game.pause_index = 1
        old_seed = game.maze.seed
        game.score = 100
        game._handle_keydown(pygame.K_RETURN)
        self.assertEqual(GameState.PLAYING, game.state)
        self.assertEqual(0, game.score)
        self.assertNotEqual(old_seed, game.maze.seed)

        game._handle_keydown(pygame.K_p)
        old_labels = game.show_power_labels
        game.pause_index = 7
        game._handle_keydown(pygame.K_RETURN)
        self.assertNotEqual(old_labels, game.show_power_labels)
        self.assertEqual(game.show_power_labels, game.maze.show_power_labels)

        game.pause_index = 2
        game._handle_keydown(pygame.K_RETURN)
        self.assertEqual(GameState.MENU, game.state)

    def test_eaten_enemy_rejoins_same_power_session_and_is_edible(self):
        game = Game(pygame.display.get_surface())
        enemy = game.enemies[0]
        game.power_timer = POWER_DURATION
        enemy.frighten(POWER_DURATION)
        game._eat_ghost(enemy)

        self.assertEqual(Enemy.MODE_RESPAWNING, enemy.mode)
        self.assertFalse(enemy.collides_with_player(game.player))

        for _ in range(ENEMY_RESPAWN_FRAMES):
            enemy.update(game.player, game.level)

        self.assertEqual(Enemy.MODE_SCARED, enemy.mode)
        self.assertGreater(enemy.scared_timer, 0)
        enemy.x, enemy.y = game.player.x, game.player.y
        self.assertTrue(enemy.collides_with_player(game.player))

    def test_power_end_cancels_respawn_vulnerability(self):
        game = Game(pygame.display.get_surface())
        enemy = game.enemies[0]
        enemy.respawn_after_eaten(POWER_DURATION)
        game._end_power_mode()

        for _ in range(ENEMY_RESPAWN_FRAMES):
            enemy.update(game.player, game.level)

        self.assertEqual(Enemy.MODE_CHASE, enemy.mode)

    def test_red_chaser_catches_stationary_player_across_mazes(self):
        """Regression: learned Q values cannot farm a wall loop forever."""
        brain = load_brains()[0]
        for seed in (42, 100, 200, 300, 400, 500, 600, 786125176):
            maze = Maze(seed=seed)
            player = Player(maze)
            enemy = Enemy(0, maze, brain)
            caught_at = None
            for frame in range(60 * 90):
                enemy.update(player, 1)
                if enemy.collides_with_player(player):
                    caught_at = frame
                    break
            self.assertIsNotNone(caught_at, f"seed={seed}")


if __name__ == "__main__":
    unittest.main()
