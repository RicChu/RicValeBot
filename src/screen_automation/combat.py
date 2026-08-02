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


class PrioritySkillGroup:
    """Selects one ready skill in configured priority order."""

    def __init__(self, skills: tuple[tuple[str, float], ...], interval_seconds: float) -> None:
        if not skills or interval_seconds <= 0:
            raise ValueError("skill group requires skills and a positive interval")
        if any(not key or cooldown_seconds <= 0 for key, cooldown_seconds in skills):
            raise ValueError("skill group entries require a key and positive cooldown")
        self.skills = skills
        self.interval_seconds = interval_seconds
        self._last_group_cast = float("-inf")
        self._last_skill_cast = {key: float("-inf") for key, _ in skills}

    def next_skill(self, now: float) -> str | None:
        if now - self._last_group_cast < self.interval_seconds - 1e-9:
            return None
        for key, cooldown_seconds in self.skills:
            if now - self._last_skill_cast[key] >= cooldown_seconds - 1e-9:
                self._last_group_cast = now
                self._last_skill_cast[key] = now
                return key
        return None


class CrowdSkillGroup:
    def __init__(
        self,
        keys: tuple[str, ...],
        min_targets: int,
        skill_cooldown_seconds: float,
        spacing_seconds: float,
        skills: tuple[tuple[str, float], ...] | None = None,
    ) -> None:
        if not keys:
            raise ValueError("crowd skill group requires at least one key")
        selected_skills = skills or tuple((key, skill_cooldown_seconds) for key in keys)
        self.keys = tuple(key for key, _ in selected_skills)
        self.min_targets = min_targets
        if skill_cooldown_seconds <= 0:
            raise ValueError("crowd skill cooldown and spacing must be positive")
        self.skill_group = PrioritySkillGroup(selected_skills, spacing_seconds)

    def next_skill(self, now: float, target_count: int) -> str | None:
        if target_count < self.min_targets:
            return None
        return self.skill_group.next_skill(now)


class CombatController:
    def __init__(self, crowd_skills: CrowdSkillGroup) -> None:
        self.crowd_skills = crowd_skills

    def observe(self, now: float, target_count: int) -> str | None:
        return self.crowd_skills.next_skill(now, target_count)

    def should_avoid_crowd(self, target_count: int) -> bool:
        return target_count >= self.crowd_skills.min_targets
