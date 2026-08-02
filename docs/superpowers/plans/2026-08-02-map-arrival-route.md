# Map Arrival Route Implementation Plan

**Goal:** Start an active map's scripted WASD route only after its destination minimap template is visible, then use bounded random patrol after the script ends.

**Architecture:** Each map profile may define `arrival_minimap_template_path` and `arrival_minimap_threshold`. `MapArrivalWaitController` blocks movement after program-driven teleport departure until template matching finds that active map's minimap; `AutomationApp` then starts the existing scripted-route controller.

## Implemented tasks

- [x] Add `MapArrivalWaitController` with idle, waiting, arrived, and cancellation behavior.
- [x] Add optional per-map arrival-minimap configuration with validation.
- [x] Gate scripted-route start behind the active map's minimap template and release movement while waiting.
- [x] Preserve random patrol after scripted-route arrival.
- [x] Add The Forge minimap template at `assets/teleport/arrival_maps/the_forge.png`.
- [x] Add controller, app-flow, and configuration tests.
- [x] Verify with full unit tests, compileall, configuration construction, and `git diff --check`.
