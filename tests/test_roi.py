import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.config import CenterROIConfig
from screen_automation.detector import DetectionResult
from screen_automation.roi import center_roi_bounds, translate_detection


class CenterROITests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = CenterROIConfig(enabled=True, width=700, height=500, offset_y=50)

    def test_returns_centered_700_by_500_region_for_1600_by_1000_frame(self) -> None:
        self.assertEqual(center_roi_bounds(1600, 1000, self.config), (450, 300, 700, 500))

    def test_clips_region_to_small_frame_boundaries(self) -> None:
        self.assertEqual(center_roi_bounds(400, 300, self.config), (0, 0, 400, 300))

    def test_translates_roi_detection_back_to_window_coordinates(self) -> None:
        local = DetectionResult(score=0.8, left=30, top=40, width=90, height=25)
        result = translate_detection(local, 450, 300)
        self.assertEqual((result.left, result.top, result.width, result.height), (480, 340, 90, 25))


if __name__ == "__main__":
    unittest.main()
