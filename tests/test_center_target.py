import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.center_target import is_inside_window_center_radius
from screen_automation.detector import DetectionResult
from screen_automation.window import WindowInfo


class CenterTargetTests(unittest.TestCase):
    def test_accepts_target_at_game_window_center_even_when_window_is_off_screen_center(self) -> None:
        window = WindowInfo(hwnd=1, title="Target", left=100, top=50, width=500, height=400)
        detection = DetectionResult(score=0.9, left=240, top=190, width=20, height=20)

        self.assertTrue(is_inside_window_center_radius(window, detection, 30))


if __name__ == "__main__":
    unittest.main()
