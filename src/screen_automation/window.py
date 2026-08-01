from __future__ import annotations

import ctypes
from dataclasses import dataclass

import numpy as np
import win32gui
import win32ui


@dataclass(frozen=True)
class WindowInfo:
    hwnd: int
    title: str
    left: int
    top: int
    width: int
    height: int


def find_window(title_fragment: str) -> WindowInfo:
    matches: list[tuple[int, str]] = []

    def collect(hwnd: int, _: int) -> None:
        title = win32gui.GetWindowText(hwnd)
        if win32gui.IsWindowVisible(hwnd) and title_fragment.casefold() in title.casefold():
            matches.append((hwnd, title))

    win32gui.EnumWindows(collect, 0)
    if not matches:
        raise RuntimeError(f"找不到標題包含「{title_fragment}」的可見視窗")
    hwnd, title = matches[0]
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    return WindowInfo(hwnd, title, left, top, right - left, bottom - top)


def capture_print_window(window: WindowInfo) -> np.ndarray:
    """使用 Win32 PrintWindow 截圖，回傳 BGR 格式影像。"""
    hdc_window = win32gui.GetWindowDC(window.hwnd)
    if not hdc_window:
        raise RuntimeError("無法取得目標視窗 DC")
    source_dc = win32ui.CreateDCFromHandle(hdc_window)
    memory_dc = source_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(source_dc, window.width, window.height)
    memory_dc.SelectObject(bitmap)
    try:
        # PW_RENDERFULLCONTENT (2) 有助於取得部分現代視窗內容。
        success = ctypes.windll.user32.PrintWindow(window.hwnd, memory_dc.GetSafeHdc(), 2)
        if not success:
            raise RuntimeError("PrintWindow 失敗")
        pixels = bitmap.GetBitmapBits(True)
        image = np.frombuffer(pixels, dtype=np.uint8).reshape(window.height, window.width, 4)
        return np.ascontiguousarray(image[:, :, :3])
    finally:
        win32gui.DeleteObject(bitmap.GetHandle())
        memory_dc.DeleteDC()
        source_dc.DeleteDC()
        win32gui.ReleaseDC(window.hwnd, hdc_window)
