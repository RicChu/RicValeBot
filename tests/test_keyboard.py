import sys
import unittest
from pathlib import Path

import win32con

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.keyboard import virtual_key


class KeyboardTests(unittest.TestCase):
    def test_supports_function_keys(self) -> None:
        self.assertEqual(virtual_key("F3"), win32con.VK_F3)
        self.assertEqual(virtual_key("f24"), win32con.VK_F24)


if __name__ == "__main__":
    unittest.main()
