import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.detector import MultiTemplateDetector


class MultiTemplateDetectorTests(unittest.TestCase):
    def test_returns_match_from_any_configured_template(self) -> None:
        frame = np.zeros((40, 60, 3), dtype=np.uint8)
        first_pattern = np.zeros((10, 10, 3), dtype=np.uint8)
        first_pattern[0, 0] = (255, 255, 255)
        second_pattern = np.zeros((10, 10, 3), dtype=np.uint8)
        second_pattern[2:8, 2:8] = (255, 255, 255)
        frame[12:22, 30:40] = second_pattern
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.png"
            second = root / "second.png"
            cv2.imwrite(str(first), first_pattern)
            cv2.imwrite(str(second), second_pattern)
            detector = MultiTemplateDetector((first, second), threshold=0.9, roi=None)

            result = detector.detect(frame)

        self.assertIsNotNone(result)
        self.assertEqual((result.left, result.top), (30, 12))

    def test_loads_all_image_templates_from_a_folder(self) -> None:
        frame = np.zeros((30, 30, 3), dtype=np.uint8)
        pattern = np.zeros((8, 8, 3), dtype=np.uint8)
        pattern[2:6, 2:6] = (255, 255, 255)
        frame[10:18, 12:20] = pattern
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir) / "target"
            folder.mkdir()
            cv2.imwrite(str(folder / "example.png"), pattern)
            detector = MultiTemplateDetector((folder,), threshold=0.9, roi=None)

            result = detector.detect(frame)

        self.assertIsNotNone(result)
        self.assertEqual((result.left, result.top), (12, 10))


if __name__ == "__main__":
    unittest.main()
