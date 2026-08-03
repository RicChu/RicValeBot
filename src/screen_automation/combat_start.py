from __future__ import annotations


class CombatStartSkillGroup:
    """Retry one ordered skill sequence until its status icon is visible."""

    def __init__(
        self,
        skills: tuple[str, ...],
        skill_interval_seconds: float,
        verify_delay_seconds: float,
    ) -> None:
        if skill_interval_seconds < 0 or verify_delay_seconds <= 0:
            raise ValueError("combat-start timing values are invalid")
        if any(not key for key in skills):
            raise ValueError("combat-start skill keys must not be empty")
        self.skills = skills
        self.skill_interval_seconds = skill_interval_seconds
        self.verify_delay_seconds = verify_delay_seconds
        self._active = False
        self._pending: list[str] = []
        self._next_skill_at = float("inf")

    def reset(self) -> None:
        self._active = False
        self._pending.clear()
        self._next_skill_at = float("inf")

    @property
    def active(self) -> bool:
        return self._active

    def trigger(self, reason: str, now: float) -> None:
        if not reason:
            raise ValueError("combat-start trigger reason must not be empty")
        self._active = True
        self._pending = list(self.skills)
        self._next_skill_at = now

    def next_skill(self, status_visible: bool, now: float) -> str | None:
        if not self._active:
            return None
        if status_visible:
            self.reset()
            return None
        if self._pending and now + 1e-9 >= self._next_skill_at:
            key = self._pending.pop(0)
            self._next_skill_at = now + (
                self.skill_interval_seconds if self._pending else self.verify_delay_seconds
            )
            return key
        if not self._pending and now + 1e-9 >= self._next_skill_at:
            self._pending = list(self.skills)
            self._next_skill_at = now
            return self.next_skill(status_visible=False, now=now)
        return None
