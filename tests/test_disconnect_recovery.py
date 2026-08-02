import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.detector import DetectionResult
from screen_automation.disconnect_recovery import DisconnectRecoveryController


class FakeDetector:
    def __init__(self, results: list[DetectionResult | None]) -> None:
        self.results = results

    def detect(self, _frame: np.ndarray) -> DetectionResult | None:
        return self.results.pop(0) if self.results else None


class DisconnectRecoveryControllerTests(unittest.TestCase):
    def test_clicks_confirmation_once_then_releases_to_login_after_dialog_closes(self) -> None:
        match = DetectionResult(0.96, 20, 40, 120, 60)
        config = SimpleNamespace(enabled=True, threshold=0.82, confirm_template_path="disconnect.png")
        controller = DisconnectRecoveryController(config, lambda _path, _threshold: FakeDetector([match, match, None]))
        frame = np.zeros((180, 240, 3), dtype=np.uint8)

        first = controller.handle(frame)
        second = controller.handle(frame)
        self.assertTrue(controller.active)
        third = controller.handle(frame)

        self.assertEqual((first.label, first.x, first.y), ("disconnect_confirm", 80, 70))
        self.assertIsNone(second)
        self.assertIsNone(third)
        self.assertFalse(controller.active)


if __name__ == "__main__":
    unittest.main()
