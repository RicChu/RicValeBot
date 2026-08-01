import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.combat import CombatController, CrowdSkillGroup, select_nearest_to_center, steer_away_from_target
from screen_automation.detector import DetectionResult


class CombatTests(unittest.TestCase):
    def test_selects_target_with_center_nearest_to_screen_center(self) -> None:
        targets = (
            DetectionResult(0.9, left=20, top=20, width=80, height=20),
            DetectionResult(0.8, left=440, top=290, width=80, height=20),
            DetectionResult(0.95, left=800, top=500, width=80, height=20),
        )

        selected = select_nearest_to_center(targets, frame_width=1000, frame_height=700)

        self.assertEqual(selected, targets[1])

    def test_uses_the_highest_priority_ready_crowd_skill(self) -> None:
        skills = CrowdSkillGroup(("F2", "F3", "F4"), min_targets=3, skill_cooldown_seconds=6.0, spacing_seconds=0.33)

        self.assertEqual(skills.next_skill(0.00, target_count=3), "F2")
        self.assertIsNone(skills.next_skill(0.20, target_count=3))
        self.assertEqual(skills.next_skill(0.33, target_count=3), "F3")
        self.assertEqual(skills.next_skill(6.00, target_count=3), "F2")

    def test_marks_only_a_crowd_as_a_movement_avoidance_condition(self) -> None:
        combat = CombatController(CrowdSkillGroup(("F3",), 3, 0.5, 0.33))

        self.assertFalse(combat.should_avoid_crowd(target_count=2))
        self.assertTrue(combat.should_avoid_crowd(target_count=3))

    def test_reflects_only_movement_components_that_approach_the_crowd(self) -> None:
        target = DetectionResult(score=0.9, left=75, top=10, width=20, height=20)

        keys = steer_away_from_target(("W", "D"), target, frame_width=100, frame_height=100)

        self.assertEqual(keys, ("S", "A"))


if __name__ == "__main__":
    unittest.main()
