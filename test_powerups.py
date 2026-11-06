import unittest

from powerups import PowerUpManager


class PowerUpTests(unittest.TestCase):
    def test_every_power_activates_and_expires(self):
        manager = PowerUpManager()
        positions = [(3, 1), (3, 25), (27, 1), (27, 25)]
        self.assertEqual(manager.assign_for_maze(42, positions),
                         manager.assign_for_maze(42, positions))

        manager.activate("shield")
        self.assertTrue(manager.consume_shield())
        self.assertFalse(manager.consume_shield())

        for key in ("overclock", "freeze", "magnet", "decoy", "chain_dash"):
            manager.activate(key, (1, 1), duration_scale=0.01)
            self.assertTrue(manager.active(key))
            while manager.active(key):
                manager.update()
            self.assertFalse(manager.active(key))


if __name__ == "__main__":
    unittest.main()
