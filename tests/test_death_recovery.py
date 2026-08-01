import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.death_recovery import DeathRecoveryController
from screen_automation.detector import DetectionResult


class FakeDetector:
    def __init__(self, results: list[DetectionResult | None]) -> None:
        self.results = results

    def detect(self, _frame: np.ndarray) -> DetectionResult | None:
        return self.results.pop(0) if self.results else None


class DeathRecoveryControllerTests(unittest.TestCase):
    def test_clicks_town_respawn_once_then_waits_for_death_dialog_to_close(self) -> None:
        match = DetectionResult(0.95, 30, 40, 40, 20)
        config = SimpleNamespace(enabled=True, threshold=0.82, town_respawn_template_path="respawn.png")
        controller = DeathRecoveryController(config, lambda _path, _threshold: FakeDetector([match, match, None]))
        frame = np.zeros((100, 100, 3), dtype=np.uint8)

        first = controller.handle(frame)
        second = controller.handle(frame)

        self.assertEqual((first.label, first.x, first.y), ("town_respawn", 50, 50))
        self.assertIsNone(second)
        self.assertTrue(controller.active)
        third = controller.handle(frame)
        self.assertIsNone(third)
        self.assertFalse(controller.active)


if __name__ == "__main__":
    unittest.main()
