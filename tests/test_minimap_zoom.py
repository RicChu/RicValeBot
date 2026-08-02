import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.minimap_zoom import MinimapZoomController


class MinimapZoomControllerTests(unittest.TestCase):
    def test_town_zoom_emits_the_configured_number_of_downward_actions(self) -> None:
        controller = MinimapZoomController(enabled=True, town_scroll_steps=2, combat_scroll_steps=3, interval_ms=10)

        controller.start_town(1.0)

        self.assertEqual(controller.next_action(1.0).direction, -1)
        self.assertIsNone(controller.next_action(1.005))
        self.assertEqual(controller.next_action(1.01).direction, -1)
        self.assertEqual(controller.consume_completion(), "town")

    def test_combat_zoom_emits_upward_actions_then_completes(self) -> None:
        controller = MinimapZoomController(
            enabled=True,
            town_scroll_steps=2,
            combat_scroll_steps=2,
            interval_ms=10,
            combat_load_wait_ms=500,
        )

        controller.start_combat(5.0)

        self.assertIsNone(controller.next_action(5.49))
        self.assertEqual(controller.next_action(5.5).direction, 1)
        self.assertEqual(controller.next_action(5.51).direction, 1)
        self.assertEqual(controller.consume_completion(), "combat")
        self.assertFalse(controller.active)

    def test_disabled_zoom_completes_without_emitting_input(self) -> None:
        controller = MinimapZoomController(enabled=False, town_scroll_steps=30, combat_scroll_steps=30, interval_ms=10)

        controller.start_town(1.0)

        self.assertIsNone(controller.next_action(1.0))
        self.assertEqual(controller.consume_completion(), "town")


if __name__ == "__main__":
    unittest.main()
