import unittest
from datetime import date

from game_modes import GameModeManager


class GameModeTests(unittest.TestCase):
    def test_time_attack_expires_and_daily_seed_is_stable(self):
        timed = GameModeManager("time_attack")
        timed.begin_run(fps=2)
        for _ in range(239):
            self.assertFalse(timed.update())
        self.assertTrue(timed.update())

        daily = GameModeManager("daily")
        today = date(2026, 11, 6)
        self.assertEqual(daily.maze_seed(3, today=today),
                         daily.maze_seed(3, today=today))
        self.assertNotEqual(daily.maze_seed(3, today=today),
                            daily.maze_seed(4, today=today))

    def test_every_requested_mode_is_available(self):
        manager = GameModeManager()
        keys = set()
        for _ in range(6):
            keys.add(manager.current.key)
            manager.cycle()
        self.assertEqual({"classic", "time_attack", "one_life", "no_dash", "daily", "endless"}, keys)


if __name__ == "__main__":
    unittest.main()
