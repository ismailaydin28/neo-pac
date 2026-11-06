import json
import tempfile
import unittest
from pathlib import Path

from profile import ProfileStore


class ProfileTests(unittest.TestCase):
    def test_profile_round_trip_and_maximum(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            profile = ProfileStore(path)
            profile.set_setting("mode", "endless")
            profile.increment("games_played")
            profile.maximum("high_score", 1200)
            profile.maximum("high_score", 800)
            profile.record_daily("2026-11-06", 900)
            profile.record_daily("2026-11-06", 400)
            self.assertTrue(profile.save())
            loaded = ProfileStore(path)
            self.assertEqual("endless", loaded.setting("mode"))
            self.assertEqual(1, loaded.stat("games_played"))
            self.assertEqual(1200, loaded.stat("high_score"))
            self.assertEqual(900, loaded.data["daily_records"]["2026-11-06"])
            self.assertEqual(1, json.loads(path.read_text())["version"])


if __name__ == "__main__":
    unittest.main()
