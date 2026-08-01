import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.walking import WalkingController


class WalkingTests(unittest.TestCase):
    def test_step_never_moves_beyond_configured_boundary(self) -> None:
        walker = WalkingController(step_distance=600, boundary_x=1200, boundary_y=1200, seed=1)

        for _ in range(30):
            walker.next_step()
            self.assertLessEqual(abs(walker.x), 600)
            self.assertLessEqual(abs(walker.y), 600)

    def test_excludes_directions_that_would_move_toward_a_crowd_before_updating_position(self) -> None:
        walker = WalkingController(step_distance=20, boundary_x=200, boundary_y=200, seed=4)

        for _ in range(20):
            keys, _ = walker.next_step(excluded_keys=("D",))
            self.assertNotIn("D", keys)
            self.assertLessEqual(abs(walker.x), 100)
            self.assertLessEqual(abs(walker.y), 100)

    def test_uses_a_boundary_valid_fallback_when_crowd_avoidance_blocks_every_direction(self) -> None:
        walker = WalkingController(step_distance=20, boundary_x=200, boundary_y=200, seed=1)

        keys, _ = walker.next_step(excluded_keys=("W", "A", "S", "D"))

        self.assertNotEqual(keys, ())
        self.assertLessEqual(abs(walker.x), 100)
        self.assertLessEqual(abs(walker.y), 100)


if __name__ == "__main__":
    unittest.main()
