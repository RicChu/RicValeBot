import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.detector import DetectionResult
from screen_automation.town_teleport import TownTeleportController


class FakeDetector:
    def __init__(self, result: DetectionResult | None) -> None:
        self.result = result

    def detect(self, _frame: np.ndarray) -> DetectionResult | None:
        return self.result


def teleport_config() -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        threshold=0.82,
        action_delay_ms=0,
        stage_timeout_ms=8000,
        town_minimap_template_path="town.png",
        consumables_template_path="consumables.png",
        waystone_template_path="waystone.png",
        waystone_confirm_template_path="confirm.png",
        destination=SimpleNamespace(name="demon_mouth", template_path="demon_mouth.png"),
    )


class TownTeleportControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.matches = {
            "town.png": DetectionResult(0.95, 80, 0, 20, 20),
            "consumables.png": DetectionResult(0.95, 10, 20, 20, 20),
            "waystone.png": DetectionResult(0.95, 30, 40, 20, 20),
            "confirm.png": DetectionResult(0.95, 40, 50, 20, 20),
            "demon_mouth.png": DetectionResult(0.95, 50, 60, 20, 20),
        }

    def test_runs_the_configured_teleport_sequence(self) -> None:
        controller = TownTeleportController(teleport_config(), lambda path, _threshold: FakeDetector(self.matches[path]))

        actions = [controller.handle(self.frame, now) for now in range(5)]

        self.assertEqual((actions[0].kind, actions[0].key), ("key", "B"))
        self.assertEqual((actions[1].kind, actions[1].label, actions[1].x, actions[1].y), ("click", "consumables", 20, 30))
        self.assertEqual((actions[2].kind, actions[2].label, actions[2].x, actions[2].y), ("double_click", "waystone", 40, 50))
        self.assertEqual((actions[3].kind, actions[3].label, actions[3].x, actions[3].y), ("click", "waystone_confirm", 50, 60))
        self.assertEqual((actions[4].kind, actions[4].label, actions[4].x, actions[4].y), ("click", "map:demon_mouth", 60, 70))

    def test_unknown_frame_does_not_start_teleport(self) -> None:
        controller = TownTeleportController(teleport_config(), lambda _path, _threshold: FakeDetector(None))

        self.assertIsNone(controller.handle(self.frame, 0))
        self.assertFalse(controller.active)

    def test_missing_next_stage_times_out_without_clicking(self) -> None:
        matches = dict(self.matches)
        matches["consumables.png"] = None
        controller = TownTeleportController(teleport_config(), lambda path, _threshold: FakeDetector(matches[path]))

        self.assertEqual(controller.handle(self.frame, 0).key, "B")
        self.assertIsNone(controller.handle(self.frame, 8.1))
        self.assertFalse(controller.active)


if __name__ == "__main__":
    unittest.main()
