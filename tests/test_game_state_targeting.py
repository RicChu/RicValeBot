import unittest
from dataclasses import replace

from src.screen_automation.game_state import MonsterSnapshot, Position3D, decode_game_state
from src.screen_automation.game_state_targeting import decide_game_state
from tests.test_game_state import encode, valid_snapshot_payload


def monster(
    runtime_id: str,
    *,
    x: float,
    z: float,
    view_x: float,
    view_z: float,
    viewport_x: float = 0.5,
    viewport_y: float = 0.5,
    viewport_depth: float = 1.0,
    alive: bool = True,
) -> MonsterSnapshot:
    return MonsterSnapshot(
        runtime_id=runtime_id,
        config_id="test-monster",
        position=Position3D(x, 2.0, z),
        health=100 if alive else 0,
        max_health=100,
        is_alive=alive,
        viewport_x=viewport_x,
        viewport_y=viewport_y,
        viewport_depth=viewport_depth,
        view_x=view_x,
        view_z=view_z,
    )


def snapshot_with(*monsters: MonsterSnapshot):
    base = decode_game_state(encode(valid_snapshot_payload()))
    return replace(base, monsters=monsters)


def decide(snapshot, *, crowd_min_targets: int = 3, avoid_crowd: bool = True):
    return decide_game_state(
        snapshot,
        client_width=1000,
        client_height=600,
        near_distance=3.0,
        far_distance=7.0,
        crowd_radius=10.0,
        crowd_min_targets=crowd_min_targets,
        avoid_crowd=avoid_crowd,
    )


class GameStateTargetingTests(unittest.TestCase):
    def test_selects_nearest_living_monster_and_projects_client_position(self) -> None:
        far = monster("far", x=20, z=20, view_x=-4, view_z=12)
        dead = monster("dead", x=11, z=20, view_x=1, view_z=1, alive=False)
        near = monster(
            "near", x=13, z=24, view_x=2, view_z=5, viewport_x=0.75, viewport_y=0.25
        )

        result = decide(snapshot_with(far, dead, near), avoid_crowd=False)

        self.assertEqual(result.target.runtime_id, "near")
        self.assertEqual(result.target_distance, 5.0)
        self.assertEqual(result.target_client_position, (750, 450))

    def test_does_not_project_a_target_behind_or_outside_camera(self) -> None:
        behind = monster("behind", x=13, z=20, view_x=1, view_z=1, viewport_depth=-1)

        result = decide(snapshot_with(behind), avoid_crowd=False)

        self.assertIsNone(result.target_client_position)

    def test_moves_toward_a_far_target_using_camera_relative_axes(self) -> None:
        target = monster("far", x=20, z=20, view_x=8, view_z=4)

        result = decide(snapshot_with(target), avoid_crowd=False)

        self.assertEqual(result.band, "far")
        self.assertEqual(result.movement_keys, ("W", "D"))

    def test_moves_away_from_a_near_target(self) -> None:
        target = monster("near", x=11, z=20, view_x=3, view_z=1)

        result = decide(snapshot_with(target), avoid_crowd=False)

        self.assertEqual(result.band, "near")
        self.assertEqual(result.movement_keys, ("S", "A"))

    def test_holds_distance_inside_band(self) -> None:
        target = monster("band", x=15, z=20, view_x=-3, view_z=5)

        result = decide(snapshot_with(target), avoid_crowd=False)

        self.assertEqual(result.band, "hold")
        self.assertEqual(result.movement_keys, ())

    def test_ignores_minor_direction_component_to_prevent_jitter(self) -> None:
        target = monster("far", x=20, z=20, view_x=1, view_z=10)

        result = decide(snapshot_with(target), avoid_crowd=False)

        self.assertEqual(result.movement_keys, ("W",))

    def test_crowd_avoidance_overrides_distance_guidance(self) -> None:
        targets = (
            monster("one", x=12, z=21, view_x=4, view_z=8),
            monster("two", x=13, z=22, view_x=2, view_z=6),
            monster("three", x=14, z=23, view_x=3, view_z=7),
            monster("outside", x=30, z=30, view_x=-10, view_z=-10),
        )

        result = decide(snapshot_with(*targets))

        self.assertEqual(result.crowd_count, 3)
        self.assertTrue(result.crowd_avoidance)
        self.assertEqual(result.movement_keys, ("S", "A"))

    def test_returns_empty_decision_without_a_living_target(self) -> None:
        result = decide(snapshot_with(monster("dead", x=11, z=20, view_x=1, view_z=1, alive=False)))

        self.assertIsNone(result.target)
        self.assertEqual(result.band, "none")
        self.assertEqual(result.movement_keys, ())


if __name__ == "__main__":
    unittest.main()
