import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from screen_automation.input_coordinator import MovementInput, SkillTapQueue

class InputCoordinatorTests(unittest.TestCase):
    def test_skill_tap_never_reissues_a_movement_key(self) -> None:
        queue = SkillTapQueue(20)
        queue.queue_tap("F2")

        with patch("screen_automation.input_coordinator.post_key_state") as state, patch("screen_automation.input_coordinator.post_key"):
            queue.process(1, 0.0)

        state.assert_not_called()

    def test_movement_controller_releases_only_changed_keys(self) -> None:
        movement = MovementInput()

        with patch("screen_automation.input_coordinator.post_key_state") as state:
            movement.set_movement(1, ("W",))
            movement.set_movement(1, ("D",))
            movement.set_movement(1, ("D",))
            movement.release(1)

        self.assertEqual(
            [call.args for call in state.call_args_list],
            [(1, "W", True), (1, "W", False), (1, "D", True), (1, "D", False)],
        )
