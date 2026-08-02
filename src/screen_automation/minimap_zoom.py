from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MinimapZoomAction:
    phase: str
    direction: int
    remaining_steps: int


class MinimapZoomController:
    """Schedules one Ctrl+wheel minimap zoom input at a time."""

    def __init__(
        self,
        enabled: bool,
        town_scroll_steps: int,
        combat_scroll_steps: int,
        interval_ms: int,
        combat_load_wait_ms: int = 0,
    ) -> None:
        self.enabled = enabled
        self.town_scroll_steps = town_scroll_steps
        self.combat_scroll_steps = combat_scroll_steps
        self.interval_seconds = interval_ms / 1000
        self.combat_load_wait_ms = combat_load_wait_ms
        self.combat_load_wait_seconds = combat_load_wait_ms / 1000
        self._phase: str | None = None
        self._remaining_steps = 0
        self._next_action_at = float("inf")
        self._completed: str | None = None

    @property
    def active(self) -> bool:
        return self._phase is not None

    def start_town(self, now: float) -> None:
        self._start("town", self.town_scroll_steps, now)

    def start_combat(self, now: float) -> None:
        self._start("combat", self.combat_scroll_steps, now + self.combat_load_wait_seconds)

    def _start(self, phase: str, steps: int, now: float) -> None:
        self._phase = phase
        self._remaining_steps = steps if self.enabled else 0
        self._next_action_at = now
        self._completed = None

    def next_action(self, now: float) -> MinimapZoomAction | None:
        if self._phase is None:
            return None
        if self._remaining_steps <= 0:
            self._complete()
            return None
        if now < self._next_action_at:
            return None
        action = MinimapZoomAction(
            phase=self._phase,
            direction=-1 if self._phase == "town" else 1,
            remaining_steps=self._remaining_steps - 1,
        )
        self._remaining_steps -= 1
        self._next_action_at = now + self.interval_seconds
        if self._remaining_steps == 0:
            self._complete()
        return action

    def _complete(self) -> None:
        if self._phase is not None:
            self._completed = self._phase
        self._phase = None
        self._remaining_steps = 0

    def consume_completion(self) -> str | None:
        completed = self._completed
        self._completed = None
        return completed

    def cancel(self) -> None:
        self._phase = None
        self._remaining_steps = 0
        self._next_action_at = float("inf")
        self._completed = None
