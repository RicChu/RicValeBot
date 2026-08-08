"""Pure targeting and movement decisions derived from game-state snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from .game_state import GameStateSnapshot, MonsterSnapshot, nearest_living_monster


@dataclass(frozen=True)
class GameStateDecision:
    target: MonsterSnapshot | None
    target_distance: float | None
    target_client_position: tuple[int, int] | None
    band: str
    movement_keys: tuple[str, ...]
    crowd_count: int
    crowd_avoidance: bool


def _camera_direction(view_x: float, view_z: float, *, away: bool) -> tuple[str, ...]:
    largest = max(abs(view_x), abs(view_z))
    if largest == 0:
        return ()
    threshold = largest * 0.25
    keys: list[str] = []
    if abs(view_z) >= threshold:
        toward = "W" if view_z > 0 else "S"
        keys.append({"W": "S", "S": "W"}[toward] if away else toward)
    if abs(view_x) >= threshold:
        toward = "D" if view_x > 0 else "A"
        keys.append({"D": "A", "A": "D"}[toward] if away else toward)
    return tuple(keys)


def _client_position(
    target: MonsterSnapshot, client_width: int, client_height: int
) -> tuple[int, int] | None:
    if target.viewport_depth <= 0:
        return None
    if not 0 <= target.viewport_x <= 1 or not 0 <= target.viewport_y <= 1:
        return None
    return (
        round(target.viewport_x * client_width),
        round((1 - target.viewport_y) * client_height),
    )


def _world_distance(snapshot: GameStateSnapshot, monster: MonsterSnapshot) -> float:
    player = snapshot.player.position
    return hypot(monster.position.x - player.x, monster.position.z - player.z)


def decide_game_state(
    snapshot: GameStateSnapshot,
    *,
    client_width: int,
    client_height: int,
    near_distance: float,
    far_distance: float,
    crowd_radius: float,
    crowd_min_targets: int,
    avoid_crowd: bool,
) -> GameStateDecision:
    target = nearest_living_monster(snapshot)
    living = tuple(
        monster
        for monster in snapshot.monsters
        if monster.is_alive and monster.health > 0
    )
    crowd = tuple(monster for monster in living if _world_distance(snapshot, monster) <= crowd_radius)
    crowd_avoidance = avoid_crowd and len(crowd) >= crowd_min_targets

    if target is None:
        return GameStateDecision(None, None, None, "none", (), len(crowd), crowd_avoidance)

    distance = _world_distance(snapshot, target)
    if distance < near_distance:
        band = "near"
        movement_keys = _camera_direction(target.view_x, target.view_z, away=True)
    elif distance > far_distance:
        band = "far"
        movement_keys = _camera_direction(target.view_x, target.view_z, away=False)
    else:
        band = "hold"
        movement_keys = ()

    if crowd_avoidance:
        average_view_x = sum(monster.view_x for monster in crowd) / len(crowd)
        average_view_z = sum(monster.view_z for monster in crowd) / len(crowd)
        movement_keys = _camera_direction(average_view_x, average_view_z, away=True)

    return GameStateDecision(
        target=target,
        target_distance=distance,
        target_client_position=_client_position(target, client_width, client_height),
        band=band,
        movement_keys=movement_keys,
        crowd_count=len(crowd),
        crowd_avoidance=crowd_avoidance,
    )
