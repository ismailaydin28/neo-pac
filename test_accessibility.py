import unittest

from accessibility import AccessibilityManager


class AccessibilityTests(unittest.TestCase):
    def test_presets_change_flash_motion_and_palette(self):
        standard = AccessibilityManager("standard").current
        reduced = AccessibilityManager("reduced_flash").current
        colorblind = AccessibilityManager("colorblind").current
        low_motion = AccessibilityManager("low_motion").current
        self.assertLess(reduced.flash_strength, standard.flash_strength)
        self.assertNotEqual(colorblind.enemy_colors, standard.enemy_colors)
        self.assertTrue(low_motion.low_motion)
        self.assertFalse(low_motion.scanlines)
        self.assertFalse(low_motion.screen_shake)


if __name__ == "__main__":
    unittest.main()
