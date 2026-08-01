from __future__ import annotations

from dataclasses import dataclass
from math import hypot

import cv2
import numpy as np


@dataclass(frozen=True)
class Waypoint:
    name: str
    x: int
    y: int


class RouteNavigator:
    def __init__(self, waypoints: tuple[Waypoint, ...], arrival_radius_px: int, movement_deadzone_px: int) -> None:
        if len(waypoints) < 2:
            raise ValueError("路線模式至少需要兩個路徑點")
        self.waypoints = waypoints
        self.arrival_radius_px = arrival_radius_px
        self.movement_deadzone_px = movement_deadzone_px
        self.previous_waypoint: str | None = None
        self.current_waypoint: str | None = None
        self.target_waypoint: Waypoint | None = None

    def next_target(self, position: tuple[int, int]) -> Waypoint:
        excluded = {self.previous_waypoint, self.current_waypoint}
        candidates = [point for point in self.waypoints if point.name not in excluded]
        if not candidates:
            candidates = [point for point in self.waypoints if point.name != self.current_waypoint]
        return min(candidates, key=lambda point: (hypot(point.x - position[0], point.y - position[1]), point.name))

    def update_target(self, position: tuple[int, int]) -> Waypoint:
        if self.target_waypoint and self._distance(position, self.target_waypoint) <= self.arrival_radius_px:
            self.previous_waypoint = self.current_waypoint
            self.current_waypoint = self.target_waypoint.name
            self.target_waypoint = None

        if self.current_waypoint is None:
            nearest = min(self.waypoints, key=lambda point: (self._distance(position, point), point.name))
            if self._distance(position, nearest) <= self.arrival_radius_px:
                self.current_waypoint = nearest.name
            else:
                self.target_waypoint = nearest

        if self.target_waypoint is None:
            self.target_waypoint = self.next_target(position)
        return self.target_waypoint

    def movement_keys(self, position: tuple[int, int]) -> tuple[str, ...]:
        target = self.target_waypoint or self.update_target(position)
        keys: list[str] = []
        if target.y < position[1] - self.movement_deadzone_px:
            keys.append("W")
        elif target.y > position[1] + self.movement_deadzone_px:
            keys.append("S")
        if target.x < position[0] - self.movement_deadzone_px:
            keys.append("A")
        elif target.x > position[0] + self.movement_deadzone_px:
            keys.append("D")
        return tuple(keys)

    @staticmethod
    def _distance(position: tuple[int, int], waypoint: Waypoint) -> float:
        return hypot(waypoint.x - position[0], waypoint.y - position[1])


def find_white_pair(minimap_bgr: np.ndarray, threshold: int, pair_max_distance_px: int) -> tuple[int, int] | None:
    gray = cv2.cvtColor(minimap_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    components, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centers: list[tuple[int, int, float]] = []
    for component in components:
        area = cv2.contourArea(component)
        if not 4 <= area <= 300:
            continue
        moments = cv2.moments(component)
        if moments["m00"]:
            centers.append((round(moments["m10"] / moments["m00"]), round(moments["m01"] / moments["m00"]), area))

    pairs = []
    for index, first in enumerate(centers):
        for second in centers[index + 1 :]:
            distance = hypot(first[0] - second[0], first[1] - second[1])
            if distance <= pair_max_distance_px and first[2] != second[2]:
                pairs.append((distance, first, second))
    if not pairs:
        return None
    _, first, second = min(pairs, key=lambda item: item[0])
    return ((first[0] + second[0]) // 2, (first[1] + second[1]) // 2)


def minimap_bounds(frame_width: int, frame_height: int, right_px: int, top_px: int, width_px: int, height_px: int) -> tuple[int, int, int, int]:
    width = min(width_px, frame_width)
    height = min(height_px, frame_height - top_px)
    left = max(0, frame_width - right_px - width)
    top = max(0, min(top_px, frame_height - height))
    return left, top, width, height
