"""Regression tests for freeze-prevention optimizations."""

import os
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("NEOPAC_PROFILE_PATH", "/tmp/neopac_performance_profile.json")

import pygame

from game import Game
from learning_ai import LearningBrain, snapshot_brains
from maze import Maze
from settings import SCREEN_H, SCREEN_W


class PerformanceRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((SCREEN_W, SCREEN_H))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_route_maps_are_shared_and_bounded(self):
        maze = Maze(seed=90210)
        first = maze.route_distances(maze.player_spawn)
        second = maze.route_distances(maze.player_spawn)
        self.assertIs(first, second)

        passable = list(maze._nav_neighbors)
        for target in passable[:40]:
            maze.route_distances(target)
        self.assertLessEqual(len(maze._route_cache), maze._route_cache_limit)

    def test_brain_snapshot_is_independent(self):
        brain = LearningBrain(0, {"state": [1.0, 2.0, 3.0, 4.0]}, steps=5)
        snapshot = snapshot_brains([brain])
        brain.q["state"][0] = 99.0
        self.assertEqual(1.0, snapshot[0].q["state"][0])

    def test_periodic_ai_save_does_not_block_frame(self):
        game = Game(pygame.display.get_surface())

        def slow_save(_brains):
            time.sleep(0.08)
            return True

        with patch("game.save_brains", side_effect=slow_save):
            started = time.perf_counter()
            self.assertTrue(game._save_ai_memory(blocking=False))
            request_ms = (time.perf_counter() - started) * 1000
            self.assertLess(request_ms, 30.0)
            game._ai_save_thread.join(timeout=1.0)
            self.assertFalse(game._ai_save_thread.is_alive())


if __name__ == "__main__":
    unittest.main()
