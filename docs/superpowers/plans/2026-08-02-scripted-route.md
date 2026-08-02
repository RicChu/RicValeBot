# Scripted Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replay a recorded WASD movement script after teleport without minimap localization.

**Architecture:** A focused `scripted_route.py` module loads YAML and advances timed segments. `AutomationApp` starts it on teleport departure and sends its movement keys through the existing independent movement input. `record_route.py` produces the YAML format from physical WASD state.

**Tech Stack:** Python 3.13, PyYAML, pywin32, unittest.

## Global Constraints

- Do not run `main.py` during verification.
- No minimap capture, feature matching, or zoom is needed for scripted routes.
- Do not retain minimap-localized route playback; this plan uses only scripted-route playback.
- Do not commit or push unless requested.

---

### Task 1: Script playback model

**Files:** Create `src/screen_automation/scripted_route.py`; create `tests/test_scripted_route.py`.

- [ ] Test loading `segments: [{keys: [W], duration_ms: 500}]` and advancing from W to a final empty key set.
- [ ] Run the test and observe import failure.
- [ ] Implement `MovementSegment`, `load_movement_script`, and `ScriptedRouteController.start(now)`, `update(now)`, `cancel()`.
- [ ] Re-run the focused test.

### Task 2: Map configuration and app flow

**Files:** Modify `src/screen_automation/config.py`, `src/screen_automation/app.py`, `config.yaml`, `tests/test_config.py`, `tests/test_app_logging.py`.

- [ ] Test that a map uses `movement_script_path` and that a script starts after departure without minimap zoom.
- [ ] Run focused tests and observe failure.
- [ ] Add `movement_script_path` to `MapProfileConfig`, add walking mode `scripted_route`, and run script keys through `MovementInput`.
- [ ] Re-run focused tests.

### Task 3: Manual recorder and documentation

**Files:** Create `record_route.py`; modify `README.md`.

- [ ] Implement F9/F10 recorder with 20ms sampling and YAML output.
- [ ] Document command, controls, output path, and required YAML switch.
- [ ] Run full unit suite, `compileall`, and `git diff --check`.
