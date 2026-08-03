import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.capture import ReusableMSSCapture


class FakeMSS:
    def __init__(self) -> None:
        self.grab_calls: list[dict[str, int]] = []
        self.closed = False

    def grab(self, monitor: dict[str, int]) -> dict[str, int]:
        self.grab_calls.append(monitor)
        return monitor

    def close(self) -> None:
        self.closed = True


class ReusableMSSCaptureTests(unittest.TestCase):
    def test_reuses_one_mss_instance_across_captures(self) -> None:
        created: list[FakeMSS] = []
        capture = ReusableMSSCapture(lambda: created.append(FakeMSS()) or created[-1])

        capture.grab({"left": 1, "top": 2, "width": 3, "height": 4})
        capture.grab({"left": 5, "top": 6, "width": 7, "height": 8})
        capture.close()

        self.assertEqual(len(created), 1)
        self.assertEqual(len(created[0].grab_calls), 2)
        self.assertTrue(created[0].closed)


if __name__ == "__main__":
    unittest.main()
