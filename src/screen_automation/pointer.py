from __future__ import annotations

import win32api

from .detector import DetectionResult
from .window import WindowInfo


def image_hover_position(
    window: WindowInfo, detection: DetectionResult, offset_y: int,
) -> tuple[int, int]:
    """將視窗內的偵測座標換算為螢幕游標座標。"""
    return (
        window.left + detection.left + detection.width // 2,
        window.top + detection.top + detection.height // 2 + offset_y,
    )


def move_cursor_to_image(
    window: WindowInfo, detection: DetectionResult, offset_y: int,
) -> tuple[int, int]:
    position = image_hover_position(window, detection, offset_y)
    win32api.SetCursorPos(position)
    return position
