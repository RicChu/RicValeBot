from __future__ import annotations

from math import hypot

from .detector import DetectionResult


def select_nearest_to_center(
    targets: tuple[DetectionResult, ...], frame_width: int, frame_height: int
) -> DetectionResult:
    if not targets:
        raise ValueError("at least one target is required")
    center_x, center_y = frame_width / 2, frame_height / 2
    return min(
        targets,
        key=lambda target: (
            hypot(target.left + target.width / 2 - center_x, target.top + target.height / 2 - center_y),
            -target.score,
        ),
    )


def steer_away_from_target(
    keys: tuple[str, ...], target: DetectionResult, frame_width: int, frame_height: int
) -> tuple[str, ...]:
    """Keep moving, but reflect only components that point toward the target."""
    target_x = target.left + target.width / 2
    target_y = target.top + target.height / 2
    replacements: dict[str, str] = {}
    if target_x > frame_width / 2:
        replacements["D"] = "A"
    elif target_x < frame_width / 2:
        replacements["A"] = "D"
    if target_y > frame_height / 2:
        replacements["S"] = "W"
    elif target_y < frame_height / 2:
        replacements["W"] = "S"
    return tuple(replacements.get(key, key) for key in keys)


def directions_toward_target(target: DetectionResult, frame_width: int, frame_height: int) -> tuple[str, ...]:
    target_x = target.left + target.width / 2
    target_y = target.top + target.height / 2
    directions: list[str] = []
    if target_x > frame_width / 2:
        directions.append("D")
    elif target_x < frame_width / 2:
        directions.append("A")
    if target_y > frame_height / 2:
        directions.append("S")
    elif target_y < frame_height / 2:
        directions.append("W")
    return tuple(directions)


class CrowdSkillGroup:
    def __init__(
        self, keys: tuple[str, ...], min_targets: int, skill_cooldown_seconds: float, spacing_seconds: float
    ) -> None:
        if not keys:
            raise ValueError("crowd skill group requires at least one key")
        self.keys = keys
        self.min_targets = min_targets
        self.skill_cooldown_seconds = skill_cooldown_seconds
        self.spacing_seconds = spacing_seconds
        self._last_group_cast = float("-inf")
        self._last_skill_cast = {key: float("-inf") for key in keys}

    def next_skill(self, now: float, target_count: int) -> str | None:
        if target_count < self.min_targets or now - self._last_group_cast < self.spacing_seconds - 1e-9:
            return None
        for key in self.keys:
            if now - self._last_skill_cast[key] >= self.skill_cooldown_seconds - 1e-9:
                self._last_skill_cast[key] = now
                self._last_group_cast = now
                return key
        return None


class CombatController:
    def __init__(self, crowd_skills: CrowdSkillGroup) -> None:
        self.crowd_skills = crowd_skills

    def observe(self, now: float, target_count: int) -> str | None:
        return self.crowd_skills.next_skill(now, target_count)

    def should_avoid_crowd(self, target_count: int) -> bool:
        return target_count >= self.crowd_skills.min_targets
