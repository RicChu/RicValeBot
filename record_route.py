from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import win32api

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from screen_automation.scripted_route import MovementSegment, write_movement_script


KEYS = (("W", 0x57), ("A", 0x41), ("S", 0x53), ("D", 0x44))
START_KEY = 0x78  # F9
STOP_KEY = 0x79  # F10


def pressed_movement_keys() -> tuple[str, ...]:
    return tuple(name for name, virtual_key in KEYS if win32api.GetAsyncKeyState(virtual_key) & 0x8000)


def append_segment(segments: list[MovementSegment], keys: tuple[str, ...], started_at: float, now: float) -> None:
    duration_ms = round((now - started_at) * 1000)
    if duration_ms <= 0:
        return
    if segments and segments[-1][0] == keys:
        previous_keys, previous_duration_ms = segments[-1]
        segments[-1] = (previous_keys, previous_duration_ms + duration_ms)
    else:
        segments.append((keys, duration_ms))


def trim_idle_segments(segments: list[MovementSegment]) -> tuple[MovementSegment, ...]:
    while segments and not segments[0][0]:
        segments.pop(0)
    while segments and not segments[-1][0]:
        segments.pop()
    return tuple(segments)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record physical WASD movement into a scripted-route YAML file.")
    parser.add_argument("--output", type=Path, required=True, help="YAML file to create, for example assets/maps/the_forge/movement.yaml")
    parser.add_argument("--sample-ms", type=int, default=20, help="Keyboard sampling interval in milliseconds")
    args = parser.parse_args()
    if args.sample_ms <= 0:
        raise SystemExit("--sample-ms must be positive")

    print("Focus the game. Press F9 to start recording WASD. Press F10 to stop and save.")
    recording = False
    previous_keys: tuple[str, ...] = ()
    segment_started_at = 0.0
    segments: list[MovementSegment] = []
    while True:
        now = time.monotonic()
        if not recording and win32api.GetAsyncKeyState(START_KEY) & 1:
            recording = True
            previous_keys = pressed_movement_keys()
            segment_started_at = now
            segments.clear()
            print("Recording started.")
        elif recording and win32api.GetAsyncKeyState(STOP_KEY) & 1:
            append_segment(segments, previous_keys, segment_started_at, now)
            route = trim_idle_segments(segments)
            if not route:
                print("No WASD movement recorded; nothing written.")
            else:
                write_movement_script(args.output, route)
                print(f"Saved {len(route)} movement segments to {args.output}")
            return
        elif recording:
            current_keys = pressed_movement_keys()
            if current_keys != previous_keys:
                append_segment(segments, previous_keys, segment_started_at, now)
                previous_keys = current_keys
                segment_started_at = now
        time.sleep(args.sample_ms / 1000)


if __name__ == "__main__":
    main()
