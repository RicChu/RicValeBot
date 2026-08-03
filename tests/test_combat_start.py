import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.combat_start import CombatStartSkillGroup


class CombatStartSkillGroupTests(unittest.TestCase):
    def test_retries_the_skill_group_until_the_status_icon_appears(self) -> None:
        skills = CombatStartSkillGroup(("4", "F2"), skill_interval_seconds=0.33, verify_delay_seconds=0.50)

        skills.trigger("death_recovery", 0.0)

        self.assertEqual(skills.next_skill(status_visible=False, now=0.0), "4")
        self.assertIsNone(skills.next_skill(status_visible=False, now=0.20))
        self.assertEqual(skills.next_skill(status_visible=False, now=0.33), "F2")
        self.assertIsNone(skills.next_skill(status_visible=False, now=0.60))
        self.assertEqual(skills.next_skill(status_visible=False, now=0.83), "4")
        self.assertIsNone(skills.next_skill(status_visible=True, now=0.84))
        self.assertFalse(skills.active)

    def test_target_detection_does_not_start_the_recovery_skill_group(self) -> None:
        skills = CombatStartSkillGroup(("4",), skill_interval_seconds=0.33, verify_delay_seconds=0.50)

        self.assertIsNone(skills.next_skill(status_visible=False, now=0.0))
        self.assertFalse(skills.active)


if __name__ == "__main__":
    unittest.main()
