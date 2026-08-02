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


def ctrl_wheel_at(position: tuple[int, int], direction: int) -> tuple[int, int]:
    """Sends one Ctrl+mouse-wheel tick at the screen position.

    A positive direction zooms in; a negative direction zooms out.
    """
    if direction == 0:
        raise ValueError("Wheel direction must not be zero")
    win32api.SetCursorPos(position)
    delta = win32con.WHEEL_DELTA if direction > 0 else -win32con.WHEEL_DELTA
    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
    try:
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
    finally:
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    return position
