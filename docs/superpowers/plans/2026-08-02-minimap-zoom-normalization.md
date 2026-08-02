# Minimap Zoom Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize minimap scale before town teleport and combat-map activity.

**Architecture:** Keep zoom state in a dedicated controller, emit one wheel action per permitted interval, and let `AutomationApp` own screen-relative cursor positions and lifecycle ordering.

**Tech Stack:** Python 3.13, PyYAML, pywin32, unittest.

## Global Constraints

- Preserve all existing uncommitted user assets and route recordings.
- Do not run `main.py`; it can send real game input.
- In dry-run mode no mouse wheel or Ctrl key event is sent.

---

### Task 1: Zoom state and settings

**Files:**
- Create: `src/screen_automation/minimap_zoom.py`
- Modify: `src/screen_automation/config.py`
- Modify: `tests/test_config.py`
- Test: `tests/test_minimap_zoom.py`

- [ ] Write failing tests for up/down directions, count, interval, completion, and config parsing.
- [ ] Run the focused tests and confirm they fail because the controller/config does not exist.
- [ ] Implement `MinimapZoomController.start_town()`, `start_combat()`, `next_action(now)`, `consume_completion()`, and `cancel()`; add validated `MinimapZoomConfig` loading.
- [ ] Re-run focused tests and confirm they pass.

### Task 2: Physical input and lifecycle wiring

**Files:**
- Modify: `src/screen_automation/pointer.py`
- Modify: `src/screen_automation/town_teleport.py`
- Modify: `src/screen_automation/app.py`
- Modify: `tests/test_town_teleport.py`
- Modify: `tests/test_app_logging.py`

- [ ] Write failing tests for public town-screen detection and deferred route start until combat zoom completion.
- [ ] Run focused tests and confirm they fail.
- [ ] Add `ctrl_wheel_at`, public `TownTeleportController.is_town`, and application lifecycle integration.
- [ ] Re-run focused tests and confirm they pass.

### Task 3: User configuration and regression verification

**Files:**
- Modify: `config.yaml`
- Modify: `README.md`

- [ ] Add the enabled 100-step town-up/combat-down configuration with concise comments.
- [ ] Document the sequence and dry-run behavior.
- [ ] Run all tests, compilation, and `git diff --check`.
