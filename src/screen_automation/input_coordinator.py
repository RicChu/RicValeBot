from __future__ import annotations

from .keyboard import post_key, post_key_state


class MovementInput:
    """Owns only held WASD state for one game window."""

    def __init__(self) -> None:
        self.held: set[str] = set()

    def set_movement(self, hwnd: int, keys: tuple[str, ...]) -> None:
        desired = set(keys)
        for key in self.held - desired:
            post_key_state(hwnd, key, False)
        for key in desired - self.held:
            post_key_state(hwnd, key, True)
        self.held = desired

    def release(self, hwnd: int) -> None:
        for key in self.held:
            post_key_state(hwnd, key, False)
        self.held.clear()


class SkillTapQueue:
    """Owns queued skill taps and never changes held movement keys."""

    def __init__(self, interval_ms: int) -> None:
        self.interval = interval_ms / 1000
        self.queue: list[str] = []
        self.last = float("-inf")

    def queue_tap(self, key: str, coalesce: bool = False) -> None:
        if not coalesce or key not in self.queue:
            self.queue.append(key)

    def process(self, hwnd: int, now: float) -> None:
        if self.queue and now - self.last >= self.interval:
            post_key(hwnd, self.queue.pop(0), 0)
            self.last = now

    def clear(self) -> None:
        self.queue.clear()
