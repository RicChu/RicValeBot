import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.combat_state import CombatStateController
from screen_automation.detector import DetectionResult


class FakeDetector:
    def __init__(self, result: DetectionResult | None) -> None:
        self.result = result
        self.frame_shapes: list[tuple[int, ...]] = []

    def detect(self, frame: np.ndarray) -> DetectionResult | None:
        self.frame_shapes.append(frame.shape)
        return self.result


class CombatStateControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.config = SimpleNamespace(
            enabled=True,
            threshold=0.85,
            template_path="battle.png",
            absence_timeout_ms=10_000,
            key="4",
            roi=(0, 0, 40, 30),
        )

    def test_missing_state_for_ten_seconds_returns_key_action_once(self) -> None:
        controller = CombatStateController(self.config, lambda *_: FakeDetector(None))

        self.assertIsNone(controller.handle(self.frame, 0.0))
        self.assertIsNone(controller.handle(self.frame, 9.99))
        self.assertEqual(controller.handle(self.frame, 10.0).key, "4")
        self.assertIsNone(controller.handle(self.frame, 10.01))

    def test_detected_state_resets_the_absence_timer(self) -> None:
        detector = FakeDetector(None)
        controller = CombatStateController(self.config, lambda *_: detector)

        self.assertIsNone(controller.handle(self.frame, 0.0))
        detector.result = DetectionResult(0.95, 1, 1, 10, 10)
        self.assertIsNone(controller.handle(self.frame, 9.0))
        detector.result = None
        self.assertIsNone(controller.handle(self.frame, 18.99))
        self.assertEqual(controller.handle(self.frame, 19.0).key, "4")

    def test_checks_only_the_configured_top_left_roi(self) -> None:
        detector = FakeDetector(None)
        controller = CombatStateController(self.config, lambda *_: detector)

        controller.handle(self.frame, 0.0)

        self.assertEqual(detector.frame_shapes, [(30, 40, 3)])


if __name__ == "__main__":
    unittest.main()
