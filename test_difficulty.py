import unittest

from difficulty import DifficultyManager


class DifficultyTests(unittest.TestCase):
    def test_all_difficulties_change_real_gameplay_values(self):
        manager = DifficultyManager("casual")
        seen = set()
        for _ in range(4):
            item = manager.current
            seen.add((item.key, item.enemy_speed, item.power_scale, item.starting_lives))
            manager.cycle()
        self.assertEqual(4, len(seen))
        self.assertGreater(DifficultyManager("nightmare").current.enemy_speed,
                           DifficultyManager("normal").current.enemy_speed)


if __name__ == "__main__":
    unittest.main()
