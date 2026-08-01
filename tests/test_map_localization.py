import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import yaml

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.map_localization import MapLocalizer
from screen_automation.map_recording import MapFrame, MapManifest
from screen_automation.app import AutomationApp
from tests.test_map_recording import patterned_image, translated


def prepared_localizer(directory: Path, origin: tuple[int, int], max_jump: int = 50) -> tuple[MapLocalizer, object]:
    image = patterned_image()
    cv2.imwrite(str(directory / "frame.png"), image)
    manifest = MapManifest(
        origin_x=0,
        origin_y=0,
        width=image.shape[1],
        height=image.shape[0],
        frames=(MapFrame(index=0, x=origin[0], y=origin[1], image_path="frame.png"),),
    )
    (directory / "manifest.yaml").write_text(
        yaml.safe_dump(
            {
                "origin_x": manifest.origin_x,
                "origin_y": manifest.origin_y,
                "width": manifest.width,
                "height": manifest.height,
                "frames": [{"index": 0, "x": origin[0], "y": origin[1], "image_path": "frame.png"}],
            }
        ),
        encoding="utf-8",
    )
    return MapLocalizer(directory / "manifest.yaml", min_match_count=6, max_position_jump_px=max_jump), image


class MapLocalizationTests(unittest.TestCase):
    def test_locates_matching_minimap_at_its_recorded_canvas_origin(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            localizer, image = prepared_localizer(Path(temp_dir), origin=(120, 50))

            self.assertEqual(localizer.locate(image), (120, 50))

    def test_rejects_a_single_large_location_jump(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            localizer, image = prepared_localizer(Path(temp_dir), origin=(120, 50), max_jump=20)

            self.assertEqual(localizer.locate(image), (120, 50))
            self.assertIsNone(localizer.locate(translated(image, -100, 0)))

    def test_route_position_is_unavailable_when_map_localization_fails(self) -> None:
        app = object.__new__(AutomationApp)
        app.localizer = type("UnavailableLocalizer", (), {"locate": lambda self, _: None})()

        self.assertIsNone(app._route_player_position(patterned_image(), (40, 60)))


if __name__ == "__main__":
    unittest.main()
