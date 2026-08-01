from __future__ import annotations

import time

import win32api
import win32con
import win32gui


SPECIAL_KEYS = {
    "SPACE": win32con.VK_SPACE, "ENTER": win32con.VK_RETURN, "ESC": win32con.VK_ESCAPE,
    "LEFT": win32con.VK_LEFT, "RIGHT": win32con.VK_RIGHT, "UP": win32con.VK_UP,
    "DOWN": win32con.VK_DOWN, "TAB": win32con.VK_TAB,
}


def virtual_key(key: str) -> int:
    normalized = key.upper().strip()
    if normalized in SPECIAL_KEYS:
        return SPECIAL_KEYS[normalized]
    if normalized.startswith("F") and normalized[1:].isdigit():
        number = int(normalized[1:])
        if 1 <= number <= 24:
            return win32con.VK_F1 + number - 1
    if len(normalized) == 1 and normalized.isalnum():
        return ord(normalized)
    raise ValueError(f"不支援的按鍵名稱：{key}")


def post_key(hwnd: int, key: str, hold_ms: int) -> None:
    """向目標視窗佇列發送標準 WM_KEYDOWN/WM_KEYUP 訊息。"""
    vk = virtual_key(key)
    scan_code = win32api.MapVirtualKey(vk, 0)
    lparam_down = 1 | (scan_code << 16)
    lparam_up = lparam_down | (1 << 30) | (1 << 31)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam_down)
    time.sleep(max(0, hold_ms) / 1000)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, lparam_up)


def post_key_state(hwnd: int, key: str, pressed: bool) -> None:
    vk = virtual_key(key)
    scan_code = win32api.MapVirtualKey(vk, 0)
    lparam = 1 | (scan_code << 16)
    if pressed:
        win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, lparam)
    else:
        win32gui.PostMessage(hwnd, win32con.WM_KEYUP, vk, lparam | (1 << 30) | (1 << 31))
