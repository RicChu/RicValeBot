# Scripted Route Design

## Goal

Replace map-image localization playback with deterministic WASD segments recorded by the user.

## Runtime

The selected map may define `movement_script_path`. When `walking.mode` is `scripted_route`, a completed town teleport starts the script immediately and bypasses minimap zoom/localization. Each segment holds its configured WASD set for its duration; the final segment releases all movement keys.

## Recorder

`record_route.py` listens only while recording is enabled: F9 starts a recording and F10 writes YAML. It samples physical WASD state, records state changes with durations, removes leading/trailing idle time, and writes `segments` containing `keys` and `duration_ms`.

## Safety

The script is map-specific, starts only after the automation itself completes a teleport, and stops on death/login/teleport pause through the existing movement release path. A map with no script continues using the selected normal walking mode.
