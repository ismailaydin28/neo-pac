import unittest

from sentinel_abilities import SentinelAbility


class SentinelAbilityTests(unittest.TestCase):
    def test_every_personality_telegraphs_before_activation(self):
        for personality in range(4):
            ability = SentinelAbility(personality)
            saw_telegraph = False
            saw_active = False
            for _ in range(720):
                ability.update()
                if ability.telegraph:
                    saw_telegraph = True
                if ability.active:
                    saw_active = True
                    self.assertTrue(saw_telegraph)
                    break
            self.assertTrue(saw_active, personality)

    def test_vulnerability_disables_ability(self):
        ability = SentinelAbility(0)
        for _ in range(550):
            ability.update()
        self.assertTrue(ability.active)
        self.assertEqual(1.0, ability.update(vulnerable=True))
        self.assertFalse(ability.active)


if __name__ == "__main__":
    unittest.main()
