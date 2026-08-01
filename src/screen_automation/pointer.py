from __future__ import annotations

import time

import win32api
import win32con

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


def click_screen_position(position: tuple[int, int]) -> tuple[int, int]:
    win32api.SetCursorPos(position)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    return position


def double_click_screen_position(position: tuple[int, int]) -> tuple[int, int]:
    click_screen_position(position)
    time.sleep(0.05)
    click_screen_position(position)
    return position
