import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.timing import remaining_poll_sleep_seconds


class PollingTests(unittest.TestCase):
    def test_only_sleeps_for_the_unspent_part_of_the_poll_interval(self) -> None:
        self.assertAlmostEqual(remaining_poll_sleep_seconds(20, started_at=10.0, now=10.005), 0.015)
        self.assertEqual(remaining_poll_sleep_seconds(20, started_at=10.0, now=10.025), 0.0)


if __name__ == "__main__":
    unittest.main()
