import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.detector import DetectionResult
from screen_automation.pointer import image_hover_position
from screen_automation.window import WindowInfo


class PointerPositionTests(unittest.TestCase):
    def test_places_cursor_twenty_pixels_above_detected_image_center(self) -> None:
        window = WindowInfo(hwnd=1, title="Target", left=100, top=200, width=500, height=400)
        detection = DetectionResult(score=0.95, left=30, top=40, width=20, height=10)

        self.assertEqual(image_hover_position(window, detection, offset_y=-20), (140, 225))


if __name__ == "__main__":
    unittest.main()
