# Town Teleport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for inline execution. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** From the configured town minimap, automatically open the inventory and use a Waystone to select a configured destination map.

**Architecture:** `TownTeleportController` is a pure image-driven state machine. It yields exactly one key, click, or double-click action per stage and remains active until the town minimap disappears or a stage times out. `AutomationApp` gives it priority over combat, walking, and login-free normal play, while the existing input primitives deliver its actions.

**Tech Stack:** Python 3.13, OpenCV template matching, PyYAML, pywin32, unittest.

## Global Constraints

- Town recognition is based on the supplied top-right minimap image.
- The consumable selection is based only on the supplied icon, not text.
- Destination thumbnails live in `assets/teleport/maps/` and are selected through YAML.
- While teleporting, release WASD and clear queued skills.
- A missing expected image must time out without arbitrary clicking.

---

### Task 1: State machine and tests

**Files:**
- Create: `src/screen_automation/town_teleport.py`
- Create: `tests/test_town_teleport.py`

- [ ] Write a failing test asserting this exact action order:

```python
assert controller.handle(frame, 0).key == "B"
assert controller.handle(frame, 1).label == "consumables"
assert controller.handle(frame, 2).kind == "double_click"
assert controller.handle(frame, 3).label == "waystone_confirm"
assert controller.handle(frame, 4).label == "map:demon_mouth"
```

- [ ] Run `..\\.venv\\Scripts\\python.exe -m unittest tests.test_town_teleport -v` and verify it fails because the module does not exist.
- [ ] Implement `TeleportAction` and `TownTeleportController.handle(frame, now)` with state-specific template checks and timeout reset.
- [ ] Run the focused test again and verify it passes.

### Task 2: Config, assets, and application integration

**Files:**
- Modify: `src/screen_automation/config.py`
- Modify: `config.yaml`
- Create: `assets/teleport/city_minimap.png`
- Create: `assets/teleport/consumables.png`
- Create: `assets/teleport/waystone.png`
- Create: `assets/teleport/waystone_confirm.png`
- Create: `assets/teleport/maps/demon_mouth.png`
- Modify: `src/screen_automation/app.py`
- Modify: `src/screen_automation/pointer.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_app_logging.py`

- [ ] Add a failing config test for `town_teleport.destination.name == "demon_mouth"`.
- [ ] Add config dataclasses and the YAML section with a 0.82 threshold, 700 ms stage delay, and 8 second stage timeout.
- [ ] Crop or copy the supplied templates into the stated folders without modifying existing `assets/login/` files.
- [ ] Add `double_click_screen_position` and wire `B`, clicks, and double-clicks through an application handler that pauses movement and skills.
- [ ] Run the affected tests and verify they pass.

### Task 3: Documentation and full verification

**Files:**
- Modify: `README.md`
- Test: `tests/`

- [ ] Document the workflow, settings, and map-folder convention.
- [ ] Run `..\\.venv\\Scripts\\python.exe -m unittest discover -s tests -t . -v`.
- [ ] Run `git diff --check` and report all uncommitted user-owned asset changes separately from the teleport feature.
