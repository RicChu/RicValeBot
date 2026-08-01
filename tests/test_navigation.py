import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.navigation import RouteNavigator, Waypoint, find_white_pair, minimap_bounds


class RouteNavigatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.points = (
            Waypoint("A", 0, 0),
            Waypoint("B", 10, 0),
            Waypoint("C", 20, 0),
            Waypoint("D", 10, 20),
        )

    def test_selects_nearest_unvisited_neighbor_not_previous_station(self) -> None:
        navigator = RouteNavigator(self.points, arrival_radius_px=2, movement_deadzone_px=1)
        navigator.previous_waypoint = "A"
        navigator.current_waypoint = "B"

        target = navigator.next_target((10, 0))

        self.assertEqual(target.name, "C")

    def test_uses_both_axes_to_move_toward_current_target(self) -> None:
        navigator = RouteNavigator(self.points, arrival_radius_px=2, movement_deadzone_px=1)
        navigator.target_waypoint = Waypoint("C", 20, 0)

        self.assertEqual(navigator.movement_keys((10, 10)), ("W", "D"))

    def test_finds_center_of_nearby_large_and_small_white_marker_pair(self) -> None:
        import cv2
        import numpy as np

        minimap = np.zeros((80, 100, 3), dtype=np.uint8)
        cv2.circle(minimap, (40, 40), 4, (255, 255, 255), -1)
        cv2.circle(minimap, (49, 42), 2, (255, 255, 255), -1)

        position = find_white_pair(minimap, threshold=220, pair_max_distance_px=16)

        self.assertEqual(position, (44, 41))

    def test_places_minimap_relative_to_right_edge(self) -> None:
        self.assertEqual(minimap_bounds(2560, 1440, right_px=20, top_px=20, width_px=330, height_px=330), (2210, 20, 330, 330))


if __name__ == "__main__":
    unittest.main()
