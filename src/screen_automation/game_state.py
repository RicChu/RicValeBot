"""Read-only SpiritVale game-state snapshot protocol."""

from __future__ import annotations

import json
import math
import socket
from dataclasses import dataclass
from typing import Any


SUPPORTED_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Position3D:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class PlayerSnapshot:
    character_id: str
    position: Position3D
    health: int
    max_health: int


@dataclass(frozen=True)
class MonsterSnapshot:
    runtime_id: str
    config_id: str
    position: Position3D
    health: int
    max_health: int
    is_alive: bool


@dataclass(frozen=True)
class InventorySummary:
    equips: int
    artifacts: int
    cards: int
    gems: int
    junks: int
    consumables: int
    cosmetics: int


@dataclass(frozen=True)
class GameStateSnapshot:
    schema_version: int
    sequence: int
    captured_at_unix_ms: int
    map_id: str | None
    player: PlayerSnapshot
    monsters: tuple[MonsterSnapshot, ...]
    inventory: InventorySummary
    equipped_ids: tuple[str, ...]
    artifact_ids: tuple[str, ...]


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def _position(raw: dict[str, Any], field: str) -> Position3D:
    return Position3D(
        x=_finite_number(raw.get("x"), f"{field}.x"),
        y=_finite_number(raw.get("y"), f"{field}.y"),
        z=_finite_number(raw.get("z"), f"{field}.z"),
    )


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    return tuple(_string(item, f"{field}[]") for item in value)


def decode_game_state(payload: bytes) -> GameStateSnapshot:
    raw = _object(json.loads(payload.decode("utf-8")), "snapshot")
    schema_version = _integer(raw.get("schema_version"), "schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(f"unsupported schema_version: {schema_version}")

    player_raw = _object(raw.get("player"), "player")
    player = PlayerSnapshot(
        character_id=_string(player_raw.get("character_id"), "player.character_id"),
        position=_position(player_raw, "player"),
        health=_integer(player_raw.get("health"), "player.health"),
        max_health=_integer(player_raw.get("max_health"), "player.max_health"),
    )

    monsters_raw = raw.get("monsters", [])
    if not isinstance(monsters_raw, list):
        raise ValueError("monsters must be an array")
    monsters: list[MonsterSnapshot] = []
    for index, value in enumerate(monsters_raw):
        monster_raw = _object(value, f"monsters[{index}]")
        alive = monster_raw.get("is_alive")
        if not isinstance(alive, bool):
            raise ValueError(f"monsters[{index}].is_alive must be a boolean")
        monsters.append(
            MonsterSnapshot(
                runtime_id=_string(monster_raw.get("runtime_id"), f"monsters[{index}].runtime_id"),
                config_id=_string(monster_raw.get("config_id"), f"monsters[{index}].config_id"),
                position=_position(monster_raw, f"monsters[{index}]"),
                health=_integer(monster_raw.get("health"), f"monsters[{index}].health"),
                max_health=_integer(monster_raw.get("max_health"), f"monsters[{index}].max_health"),
                is_alive=alive,
            )
        )

    inventory_raw = _object(raw.get("inventory", {}), "inventory")
    inventory = InventorySummary(
        equips=_integer(inventory_raw.get("equips", 0), "inventory.equips"),
        artifacts=_integer(inventory_raw.get("artifacts", 0), "inventory.artifacts"),
        cards=_integer(inventory_raw.get("cards", 0), "inventory.cards"),
        gems=_integer(inventory_raw.get("gems", 0), "inventory.gems"),
        junks=_integer(inventory_raw.get("junks", 0), "inventory.junks"),
        consumables=_integer(inventory_raw.get("consumables", 0), "inventory.consumables"),
        cosmetics=_integer(inventory_raw.get("cosmetics", 0), "inventory.cosmetics"),
    )

    map_id = raw.get("map_id")
    if map_id is not None:
        map_id = _string(map_id, "map_id")

    return GameStateSnapshot(
        schema_version=schema_version,
        sequence=_integer(raw.get("sequence"), "sequence"),
        captured_at_unix_ms=_integer(raw.get("captured_at_unix_ms"), "captured_at_unix_ms"),
        map_id=map_id,
        player=player,
        monsters=tuple(monsters),
        inventory=inventory,
        equipped_ids=_string_tuple(raw.get("equipped_ids"), "equipped_ids"),
        artifact_ids=_string_tuple(raw.get("artifact_ids"), "artifact_ids"),
    )


def nearest_living_monster(snapshot: GameStateSnapshot) -> MonsterSnapshot | None:
    player = snapshot.player.position
    living = (monster for monster in snapshot.monsters if monster.is_alive and monster.health > 0)
    return min(
        living,
        key=lambda monster: math.hypot(monster.position.x - player.x, monster.position.z - player.z),
        default=None,
    )


def receive_game_state(sock: socket.socket) -> GameStateSnapshot:
    """Return the next valid snapshot, skipping malformed UDP datagrams."""
    while True:
        payload, _source = sock.recvfrom(65_535)
        try:
            return decode_game_state(payload)
        except (KeyError, TypeError, UnicodeDecodeError, ValueError):
            continue
