import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.map_recording import MapManifest, MapRecorder, estimate_translation, load_manifest


def translated(image: np.ndarray, x: int, y: int) -> np.ndarray:
    matrix = np.float32([[1, 0, x], [0, 1, y]])
    return cv2.warpAffine(image, matrix, (image.shape[1], image.shape[0]))


def patterned_image() -> np.ndarray:
    image = np.zeros((180, 220, 3), dtype=np.uint8)
    generator = np.random.default_rng(42)
    for _ in range(50):
        x, y = generator.integers(20, 200), generator.integers(20, 160)
        color = tuple(int(value) for value in generator.integers(80, 255, 3))
        cv2.circle(image, (int(x), int(y)), int(generator.integers(2, 7)), color, -1)
    cv2.putText(image, "MAP", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return image


class MapRecordingTests(unittest.TestCase):
    def test_estimates_current_image_pixel_shift(self) -> None:
        base = patterned_image()

        self.assertEqual(estimate_translation(base, translated(base, 14, -9)), (14, -9))

    def test_converts_minimap_marker_to_recorded_map_coordinates(self) -> None:
        manifest = MapManifest(origin_x=20, origin_y=10, width=200, height=100, frames=())

        self.assertEqual(manifest.global_position((40, 70), (7, 5)), (47, 75))

    def test_recorder_accumulates_frame_offsets_and_writes_loadable_map(self) -> None:
        base = patterned_image()
        recorder = MapRecorder()
        self.assertTrue(recorder.add_frame(base))
        self.assertTrue(recorder.add_frame(translated(base, -12, 0)))

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = recorder.write(Path(temp_dir))
            manifest = load_manifest(manifest_path)

            self.assertEqual(manifest.frames[1].x, 12)
            self.assertTrue((Path(temp_dir) / "recorded_map.png").is_file())
            self.assertTrue((Path(temp_dir) / manifest.frames[1].image_path).is_file())


if __name__ == "__main__":
    unittest.main()
