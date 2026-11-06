import unittest
from pathlib import Path

from diagnostics import get_feature_logger


class FeatureLoggingTests(unittest.TestCase):
    def test_each_feature_uses_a_separate_rotating_log(self):
        features = (
            "powerups", "game_modes", "profile", "difficulty",
            "accessibility", "controls", "sentinel_abilities", "audio",
            "menu",
        )
        paths = set()
        for feature in features:
            logger = get_feature_logger(feature)
            self.assertTrue(logger.handlers)
            path = Path(logger.handlers[0].baseFilename)
            self.assertEqual(f"{feature}.log", path.name)
            paths.add(path)
        self.assertEqual(len(features), len(paths))


if __name__ == "__main__":
    unittest.main()
