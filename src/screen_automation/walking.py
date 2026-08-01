from __future__ import annotations

import random
from math import sqrt

from .keyboard import post_key_state


class WalkingController:
    def __init__(self, step_distance: float, boundary_x: float, boundary_y: float, seed: int | None = None) -> None:
        self.step_distance, self.boundary_x, self.boundary_y = step_distance, boundary_x, boundary_y
        self.x = self.y = 0.0; self.random = random.Random(seed); self.held: set[str] = set()

    def next_step(self, excluded_keys: tuple[str, ...] = ()) -> tuple[tuple[str, ...], float]:
        d, q = self.step_distance, self.step_distance / sqrt(2)
        choices = ((0,-d,("W",)),(0,d,("S",)),(-d,0,("A",)),(d,0,("D",)),(-q,-q,("W","A")),(q,-q,("W","D")),(-q,q,("S","A")),(q,q,("S","D")))
        valid = [v for v in choices if abs(self.x+v[0]) <= self.boundary_x/2 and abs(self.y+v[1]) <= self.boundary_y/2]
        excluded = set(excluded_keys)
        safe = [choice for choice in valid if not excluded.intersection(choice[2])]
        available = safe or valid
        if not available:
            return (), self.step_distance
        dx, dy, keys = self.random.choice(available); self.x += dx; self.y += dy
        return keys, self.step_distance

    def apply(self, hwnd: int, keys: tuple[str, ...]) -> None:
        desired = set(keys)
        for key in self.held-desired: post_key_state(hwnd,key,False)
        for key in desired-self.held: post_key_state(hwnd,key,True)
        self.held = desired

    def release(self, hwnd: int) -> None:
        for key in self.held: post_key_state(hwnd,key,False)
        self.held.clear()
