import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from controls import ControlManager


class FakeKeys:
    def __init__(self, pressed=()):
        self.pressed = set(pressed)

    def __getitem__(self, key):
        return key in self.pressed


class ControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_keyboard_layouts_and_dash_event(self):
        controls = ControlManager("wasd_arrows")
        self.assertEqual((-1, 0), controls.direction(FakeKeys((pygame.K_a,))))
        controls.cycle(2)
        self.assertEqual((0, -1), controls.direction(FakeKeys((pygame.K_i,))))
        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)
        self.assertTrue(controls.is_dash_event(event))


if __name__ == "__main__":
    unittest.main()
