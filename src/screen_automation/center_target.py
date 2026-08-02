from __future__ import annotations

from math import hypot

from .detector import DetectionResult
from .window import WindowInfo


def target_screen_position(window: WindowInfo, detection: DetectionResult) -> tuple[int, int]:
    return (
        window.left + detection.left + detection.width // 2,
        window.top + detection.top + detection.height // 2,
    )


def is_inside_window_center_radius(window: WindowInfo, detection: DetectionResult, radius_px: int) -> bool:
    """Use the game window's visible center, independent of monitor placement."""
    target_x, target_y = target_screen_position(window, detection)
    window_center_x = window.left + window.width / 2
    window_center_y = window.top + window.height / 2
    return hypot(target_x - window_center_x, target_y - window_center_y) <= radius_px
