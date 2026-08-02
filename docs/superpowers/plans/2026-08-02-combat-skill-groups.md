# Combat Skill Groups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let task 1, center-target, and crowd combat each use an ordered, independently cooled-down skill group with a configurable group interval.

**Architecture:** Represent a configured skill as `(key, cooldown_ms)` and use one reusable priority cooldown selector. The selector checks group interval first, then selects the first skill whose individual cooldown is complete. App trigger handlers obtain one selected key at most and keep their existing mouse and WASD responsibilities.

**Tech Stack:** Python 3.13, dataclasses, PyYAML, unittest.

## Global Constraints

- Do not start `main.py`; tests must not send real game input.
- A trigger queues at most one skill.
- `skill_interval_ms` applies within one trigger's group; every skill also uses its own positive `cooldown_ms`.
- Preserve old YAML fields as fallbacks when a `skills` list is absent.

---

### Task 1: Priority cooldown skill group

**Files:**
- Modify: `src/screen_automation/combat.py`
- Modify: `tests/test_combat.py`

**Interfaces:**
- Produces: `PrioritySkillGroup(skills: tuple[tuple[str, float], ...], interval_seconds: float)`.
- Produces: `next_skill(now: float) -> str | None`.

- [ ] **Step 1: Write the failing test**

```python
def test_selects_first_ready_skill_after_group_interval(self) -> None:
    skills = PrioritySkillGroup((("2", 1.0), ("3", 2.0)), interval_seconds=0.33)
    self.assertEqual(skills.next_skill(0.0), "2")
    self.assertIsNone(skills.next_skill(0.2))
    self.assertEqual(skills.next_skill(0.33), "3")
    self.assertEqual(skills.next_skill(1.0), "2")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_combat`

Expected: FAIL because `PrioritySkillGroup` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
class PrioritySkillGroup:
    def __init__(self, skills, interval_seconds):
        self.skills = skills
        self.interval_seconds = interval_seconds
        self.last_group_cast = float("-inf")
        self.last_skill_cast = {key: float("-inf") for key, _ in skills}

    def next_skill(self, now):
        if now - self.last_group_cast < self.interval_seconds:
            return None
        for key, cooldown in self.skills:
            if now - self.last_skill_cast[key] >= cooldown:
                self.last_group_cast = self.last_skill_cast[key] = now
                return key
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_combat`

Expected: PASS.

### Task 2: YAML skill-group configuration

**Files:**
- Modify: `src/screen_automation/config.py`
- Modify: `config.yaml`
- Modify: `tests/test_config.py`

**Interfaces:**
- Produces: `SkillConfig(key: str, cooldown_ms: int)`.
- `ActionConfig`, `CenterTargetConfig`, and `CrowdCombatConfig` expose `skills: tuple[SkillConfig, ...]` and `skill_interval_ms: int`.

- [ ] **Step 1: Write the failing test**

```python
def test_reads_multiple_center_skills_with_individual_cooldowns(self) -> None:
    config = load_config(path_with_yaml)
    self.assertEqual(
        config.center_target.skills,
        (SkillConfig("2", 1000), SkillConfig("3", 2000)),
    )
    self.assertEqual(config.center_target.skill_interval_ms, 330)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_config`

Expected: FAIL because `skills` configuration is not parsed.

- [ ] **Step 3: Write minimal implementation**

```python
def parse_skills(raw_skills, fallback_key, fallback_cooldown_ms):
    if raw_skills is None:
        return (SkillConfig(fallback_key, fallback_cooldown_ms),)
    return tuple(SkillConfig(str(item["key"]), int(item["cooldown_ms"])) for item in raw_skills)
```

Validate non-empty keys, at least one skill, and positive cooldown and interval values. Set the current YAML defaults to one task-1 skill, one center skill, and F2/F3/F4 crowd skills.

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_config`

Expected: PASS.

### Task 3: Wire the three trigger handlers

**Files:**
- Modify: `src/screen_automation/app.py`
- Modify: `tests/test_app_logging.py`
- Modify: `README.md`

**Interfaces:**
- Consumes `PrioritySkillGroup.next_skill(now)`.
- Task 1, center target, and crowd combat queue the selected key, or do nothing if all skills are cooling down.

- [ ] **Step 1: Write failing integration tests**

```python
def test_center_target_uses_next_ready_skill_from_its_group(self) -> None:
    app = make_app_with_center_skills((SkillConfig("2", 1000), SkillConfig("3", 2000)))
    self.assertEqual(app._handle_center_target(0.0, (1, 1)), "2")
    self.assertEqual(app._handle_center_target(0.33, (1, 1)), "3")
```

Add equivalent assertions that task 1 retains mouse movement and crowd combat still respects `min_targets`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_app_logging`

Expected: FAIL because the handlers still use one configured key.

- [ ] **Step 3: Wire each handler**

Create one selector for task 1, center target, and crowd combat during `AutomationApp` construction. Queue only the selected key and log that key. Remove runtime dependence on `casts_per_second` and the older shared crowd cooldown fields.

- [ ] **Step 4: Update docs and current YAML**

Document this format in `README.md` and replace the current per-second configuration with explicit `skill_interval_ms` and `skills` lists in `config.yaml`.

- [ ] **Step 5: Run focused tests**

Run: `./.venv/Scripts/python.exe -m unittest tests.test_combat tests.test_config tests.test_app_logging`

Expected: PASS.

### Task 4: Full verification

**Files:**
- Verify only.

- [ ] **Step 1: Run complete verification**

Run: `./.venv/Scripts/python.exe -m unittest discover -s tests -t .`

Run: `./.venv/Scripts/python.exe -m compileall -q main.py record_route.py src`

Run: `git diff --check`

- [ ] **Step 2: Record evidence**

Report the exact passing test count and do not run `main.py`.
