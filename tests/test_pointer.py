import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.pointer import ctrl_wheel_at, move_cursor_to_screen_position


class PointerTests(unittest.TestCase):
    def test_moves_cursor_to_an_absolute_screen_position(self) -> None:
        with patch("screen_automation.pointer.win32api") as api:
            result = move_cursor_to_screen_position((750, 450))

        self.assertEqual(result, (750, 450))
        api.SetCursorPos.assert_called_once_with((750, 450))

    def test_ctrl_wheel_moves_cursor_holds_control_and_scrolls_in_direction(self) -> None:
        with patch("screen_automation.pointer.win32api") as api, patch("screen_automation.pointer.win32con") as con:
            con.VK_CONTROL = 17
            con.KEYEVENTF_KEYUP = 2
            con.MOUSEEVENTF_WHEEL = 2048
            con.WHEEL_DELTA = 120

            result = ctrl_wheel_at((300, 400), direction=-1)

        self.assertEqual(result, (300, 400))
        api.SetCursorPos.assert_called_once_with((300, 400))
        self.assertEqual(api.keybd_event.call_args_list, [call(17, 0, 0, 0), call(17, 0, 2, 0)])
        api.mouse_event.assert_called_once_with(2048, 0, 0, -120, 0)


if __name__ == "__main__":
    unittest.main()
