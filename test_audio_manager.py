import os
import unittest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

from audio_manager import AudioManager


class AudioManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_mute_round_trip_and_missing_sound_are_safe(self):
        audio = AudioManager(muted=False)
        self.assertTrue(audio.toggle())
        self.assertFalse(audio.play("does_not_exist"))
        self.assertFalse(audio.toggle())


if __name__ == "__main__":
    unittest.main()
