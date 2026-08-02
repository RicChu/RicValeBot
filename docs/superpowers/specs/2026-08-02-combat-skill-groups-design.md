# Combat Skill Groups Design

## Goal

Replace per-second caps with ordered skill groups for each combat trigger. Each skill has its own cooldown and each group retains a configurable interval between skill presses.

## Configuration

`action`, `center_target`, and `crowd_combat` each accept an ordered `skills` list:

```yaml
center_target:
  skill_interval_ms: 330
  skills:
    - {key: "2", cooldown_ms: 1000}
    - {key: "3", cooldown_ms: 2000}
```

The first ready item in list order is selected only after `skill_interval_ms` has elapsed since the last skill from that group. Each item starts its own cooldown only when it is sent. The example sends `2`, waits for the group interval, then sends `3` while `2` is cooling down, and returns to `2` as soon as its one-second cooldown and the group interval both complete.

## Runtime behavior

- Task 1 keeps its existing mouse movement, but sends the selected `action.skills` key.
- Center target sends the selected `center_target.skills` key without moving the mouse.
- Crowd combat requires `min_targets`, then sends the selected `crowd_combat.skills` key.
- One trigger evaluation queues at most one skill. `SkillTapQueue` remains responsible for safe key delivery and never modifies WASD.
- `skill_interval_ms` limits the gap between any two skills within the same trigger's group; `cooldown_ms` limits repeat use of an individual skill.

## Compatibility

Existing `action.key` / `repeat_interval_ms`, `center_target.key` / `repeat_interval_ms`, and `crowd_combat.keys` / `skill_cooldown_ms` are accepted as fallback configuration when `skills` is absent. New configuration uses `skills` plus `skill_interval_ms`.

## Validation and tests

- Every skill key is non-empty; every `cooldown_ms` and `skill_interval_ms` is positive.
- Tests cover priority selection, individual cooldown plus group interval, YAML parsing, and all three trigger integrations.
