import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.map_arrival_wait import MapArrivalWaitController


class MapArrivalWaitControllerTests(unittest.TestCase):
    def test_blocks_until_arrival_minimap_is_detected(self) -> None:
        controller = MapArrivalWaitController()

        controller.start()

        self.assertTrue(controller.active)
        self.assertTrue(controller.observe(False))
        self.assertFalse(controller.observe(True))
        self.assertFalse(controller.active)
        self.assertEqual(controller.state, "arrived")

    def test_cancel_makes_controller_inactive(self) -> None:
        controller = MapArrivalWaitController()
        controller.start()

        controller.cancel()

        self.assertFalse(controller.active)
        self.assertEqual(controller.state, "idle")

    def test_waits_after_arrival_before_route_is_ready(self) -> None:
        controller = MapArrivalWaitController()
        controller.start()

        self.assertTrue(controller.observe(True, now=10.0, route_start_delay_seconds=2.0))
        self.assertEqual(controller.state, "waiting_before_route")
        self.assertTrue(controller.observe(True, now=11.9, route_start_delay_seconds=2.0))
        self.assertFalse(controller.observe(True, now=12.0, route_start_delay_seconds=2.0))
        self.assertEqual(controller.state, "arrived")


if __name__ == "__main__":
    unittest.main()
