"""Authorized shared-memory demo used for the graduation-project presentation.

This module exchanges only data created by ``tools/memory_demo_target.py``.
It never opens, scans, or reads another application's process memory.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import asdict, dataclass
from multiprocessing.shared_memory import SharedMemory


SHARED_MEMORY_NAME = "ricvale_memory_demo"
SHARED_MEMORY_SIZE = 4096


@dataclass(frozen=True)
class DemoMonster:
    monster_id: str
    x: float
    y: float
    hp: int


@dataclass(frozen=True)
class DemoSnapshot:
    player_x: float
    player_y: float
    in_combat: bool
    monsters: tuple[DemoMonster, ...]


def encode_snapshot(snapshot: DemoSnapshot) -> bytes:
    return json.dumps(asdict(snapshot), separators=(",", ":")).encode("utf-8")


def decode_snapshot(payload: bytes) -> DemoSnapshot:
    raw = json.loads(payload.decode("utf-8"))
    return DemoSnapshot(
        player_x=float(raw["player_x"]),
        player_y=float(raw["player_y"]),
        in_combat=bool(raw["in_combat"]),
        monsters=tuple(DemoMonster(str(item["monster_id"]), float(item["x"]), float(item["y"]), int(item["hp"])) for item in raw["monsters"]),
    )


def write_snapshot(shared_memory: SharedMemory, snapshot: DemoSnapshot) -> None:
    payload = encode_snapshot(snapshot)
    if len(payload) > len(shared_memory.buf) - 4:
        raise ValueError("demo snapshot exceeds shared-memory capacity")
    shared_memory.buf[:4] = struct.pack("<I", 0)
    shared_memory.buf[4:4 + len(payload)] = payload
    shared_memory.buf[:4] = struct.pack("<I", len(payload))


def read_snapshot(shared_memory: SharedMemory) -> DemoSnapshot | None:
    size = struct.unpack("<I", shared_memory.buf[:4])[0]
    if size == 0:
        return None
    if size > len(shared_memory.buf) - 4:
        raise ValueError("demo shared-memory payload size is invalid")
    return decode_snapshot(bytes(shared_memory.buf[4:4 + size]))


def choose_nearest_monster(snapshot: DemoSnapshot) -> DemoMonster | None:
    living = (monster for monster in snapshot.monsters if monster.hp > 0)
    return min(living, key=lambda monster: math.hypot(monster.x - snapshot.player_x, monster.y - snapshot.player_y), default=None)


def count_nearby_monsters(snapshot: DemoSnapshot, radius: float) -> int:
    return sum(
        monster.hp > 0 and math.hypot(monster.x - snapshot.player_x, monster.y - snapshot.player_y) <= radius
        for monster in snapshot.monsters
    )
