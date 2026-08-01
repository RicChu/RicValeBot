# Login Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline execution selected by the user) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect the supplied server-selection and character-selection screens, safely click the configured server and character, and return control to normal automation once the game is entered.

**Architecture:** A focused `LoginRecoveryController` will receive one captured frame at a time and produce at most one click action. It determines the stage from action-button templates, applies a short per-action delay, and returns `True` whenever the regular combat/walking loop must be suspended. Templates and the selected server/character are declared in `config.yaml`; normal game frames have no matching login template and leave the current automation untouched.

**Tech Stack:** Python 3.13, OpenCV template matching, PyYAML, pywin32, unittest.

## Global Constraints

- Use only the supplied login screen templates; unknown screens must produce no click.
- While a known login stage is active, release WASD and clear queued skill keys before any mouse action.
- The server and character labels must be configurable in YAML; their corresponding template paths are used for image matching.
- Do not push this branch unless the user explicitly asks.

---

### Task 1: Login-recovery state machine

**Files:**
- Create: `src/screen_automation/login_recovery.py`
- Create: `tests/test_login_recovery.py`

**Interfaces:**
- Consumes: `TemplateDetector.detect(frame_bgr) -> DetectionResult | None`.
- Produces: `LoginRecoveryController.handle(frame_bgr, now) -> LoginAction | None`, where `LoginAction` contains `stage`, `label`, `x`, and `y`.

- [ ] **Step 1: Write the failing tests**

```python
def test_server_stage_selects_configured_server_before_connect():
    controller = LoginRecoveryController(config, detector_factory)
    assert controller.handle(frame, now=0).label == "server:SEA"
    assert controller.handle(frame, now=1).label == "connect"

def test_unknown_frame_returns_no_action():
    assert controller.handle(frame, now=0) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `..\\.venv\\Scripts\\python.exe -m unittest tests.test_login_recovery -v`

Expected: FAIL because `screen_automation.login_recovery` does not exist.

- [ ] **Step 3: Write the minimal implementation**

```python
class LoginRecoveryController:
    def handle(self, frame_bgr, now):
        if self._server_screen(frame_bgr):
            return self._next_server_action(frame_bgr, now)
        if self._character_screen(frame_bgr):
            return self._next_character_action(frame_bgr, now)
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `..\\.venv\\Scripts\\python.exe -m unittest tests.test_login_recovery -v`

Expected: PASS.

### Task 2: Configuration and supplied templates

**Files:**
- Modify: `src/screen_automation/config.py`
- Modify: `config.yaml`
- Create: `assets/login/server/sea.png`
- Create: `assets/login/server/connect.png`
- Create: `assets/login/character/didi_killer.png`
- Create: `assets/login/character/play.png`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `LoginRecoveryConfig` with `enabled`, thresholds, cooldown, and server/character template paths.

- [ ] **Step 1: Write a failing config test**

```python
def test_load_config_reads_login_recovery_section(tmp_path):
    config = load_config(write_config_with_login_recovery(tmp_path))
    assert config.login_recovery.server.name == "SEA"
    assert config.login_recovery.character.name == "滴滴殺手"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `..\\.venv\\Scripts\\python.exe -m unittest tests.test_config.ConfigTests.test_load_config_reads_login_recovery_section -v`

Expected: FAIL because `AppConfig` has no `login_recovery` field.

- [ ] **Step 3: Implement config parsing and crop templates from the supplied images**

```yaml
login_recovery:
  enabled: true
  threshold: 0.82
  action_delay_ms: 700
  server: {name: "SEA", template_path: assets/login/server/sea.png, connect_template_path: assets/login/server/connect.png}
  character: {name: "滴滴殺手", template_path: assets/login/character/didi_killer.png, play_template_path: assets/login/character/play.png}
```

- [ ] **Step 4: Run config test to verify it passes**

Run: `..\\.venv\\Scripts\\python.exe -m unittest tests.test_config.ConfigTests.test_load_config_reads_login_recovery_section -v`

Expected: PASS.

### Task 3: Integrate safe login actions with the application loop

**Files:**
- Modify: `src/screen_automation/app.py`
- Modify: `src/screen_automation/pointer.py`
- Modify: `tests/test_app_logging.py`

**Interfaces:**
- Consumes: `LoginRecoveryController.handle(frame_bgr, now)` and `click_at(x, y)`.
- Produces: an early-return login path that prevents target detection, movement, and skill queue processing for that iteration.

- [ ] **Step 1: Write a failing integration test**

```python
def test_login_action_releases_movement_clears_skills_and_clicks():
    app._handle_login_action(window, LoginAction("server", "connect", 100, 200))
    app.movement_input.set_movement.assert_called_once_with(window.hwnd, ())
    app.skill_input.clear.assert_called_once_with()
    click_at.assert_called_once_with(100, 200)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `..\\.venv\\Scripts\\python.exe -m unittest tests.test_app_logging -v`

Expected: FAIL because the login action handler does not exist.

- [ ] **Step 3: Implement one-action-per-frame integration and event logs**

```python
if action := self.login_recovery.handle(frame, now):
    self._handle_login_action(window, action)
    continue
```

- [ ] **Step 4: Run the affected tests to verify they pass**

Run: `..\\.venv\\Scripts\\python.exe -m unittest tests.test_login_recovery tests.test_app_logging -v`

Expected: PASS.

### Task 4: Document and verify

**Files:**
- Modify: `README.md`
- Test: `tests/`

- [ ] **Step 1: Document the YAML controls and the unknown-screen safety behavior**
- [ ] **Step 2: Run the complete suite**

Run: `..\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v`

Expected: all tests pass.

- [ ] **Step 3: Inspect the diff and commit the feature branch**

Run: `git diff --check; git status --short; git add README.md config.yaml assets/login src/screen_automation tests docs/superpowers/plans; git commit -m "feat: add login recovery automation"`
