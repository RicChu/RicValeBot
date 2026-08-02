import sys
import tempfile
import unittest
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.scripted_route import ScriptedRouteController, load_movement_script, write_movement_script


class ScriptedRouteTests(unittest.TestCase):
    def test_replays_each_wasd_segment_then_releases_keys(self) -> None:
        controller = ScriptedRouteController(((("W", "D"), 500), (("W",), 300)))

        controller.start(10.0)

        self.assertEqual(controller.update(10.0), ("W", "D"))
        self.assertEqual(controller.update(10.5), ("W",))
        self.assertEqual(controller.update(10.8), ())
        self.assertEqual(controller.state, "arrived")

    def test_loads_a_movement_script_from_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "movement.yaml"
            path.write_text(yaml.safe_dump({"segments": [{"keys": ["W", "A"], "duration_ms": 450}]}), encoding="utf-8")

            segments = load_movement_script(path)

        self.assertEqual(segments, ((("W", "A"), 450),))

    def test_writes_a_movement_script_that_can_be_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "movement.yaml"

            write_movement_script(path, ((("W",), 300), (("W", "D"), 450)))

            self.assertEqual(load_movement_script(path), ((("W",), 300), (("W", "D"), 450)))


if __name__ == "__main__":
    unittest.main()
