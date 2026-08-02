from __future__ import annotations

from pathlib import Path

import yaml


MovementSegment = tuple[tuple[str, ...], int]
_MOVEMENT_KEYS = {"W", "A", "S", "D"}


def write_movement_script(path: Path, segments: tuple[MovementSegment, ...]) -> None:
    if not segments:
        raise ValueError("movement script requires at least one segment")
    data = {
        "version": 1,
        "segments": [{"keys": list(keys), "duration_ms": duration_ms} for keys, duration_ms in segments],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_movement_script(path: Path) -> tuple[MovementSegment, ...]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    segments_raw = raw.get("segments") if isinstance(raw, dict) else None
    if not isinstance(segments_raw, list) or not segments_raw:
        raise ValueError("movement script requires a non-empty segments list")
    segments: list[MovementSegment] = []
    for item in segments_raw:
        if not isinstance(item, dict):
            raise ValueError("movement script segments must be mappings")
        keys = item.get("keys")
        duration_ms = item.get("duration_ms")
        if not isinstance(keys, list) or any(key not in _MOVEMENT_KEYS for key in keys):
            raise ValueError("movement script keys must contain only W, A, S, or D")
        if len(set(keys)) != len(keys) or not isinstance(duration_ms, int) or duration_ms <= 0:
            raise ValueError("movement script segment duration_ms must be positive")
        segments.append((tuple(keys), duration_ms))
    return tuple(segments)


class ScriptedRouteController:
    """Replays recorded WASD segments without depending on minimap localization."""

    def __init__(self, segments: tuple[MovementSegment, ...]) -> None:
        if not segments:
            raise ValueError("scripted route requires at least one segment")
        self.segments = segments
        self.state = "idle"
        self._index = 0
        self._segment_ends_at = 0.0

    @property
    def active(self) -> bool:
        return self.state == "navigating"

    @property
    def segment_index(self) -> int:
        return self._index

    def start(self, now: float) -> None:
        self.state = "navigating"
        self._index = 0
        self._segment_ends_at = now + self.segments[0][1] / 1000

    def cancel(self) -> None:
        self.state = "idle"

    def update(self, now: float) -> tuple[str, ...]:
        if not self.active:
            return ()
        while self.active and now >= self._segment_ends_at:
            self._index += 1
            if self._index >= len(self.segments):
                self.state = "arrived"
                return ()
            self._segment_ends_at += self.segments[self._index][1] / 1000
        return self.segments[self._index][0]
