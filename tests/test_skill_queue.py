import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.skill_queue import SkillScheduler


class SkillQueueTests(unittest.TestCase):
    def test_startup_queue_excludes_periodic_two(self) -> None:
        scheduler = SkillScheduler(queue_interval_ms=330, schedules=(("6", 45), ("5", 20), ("6", 20), ("V", 0.5)))
        scheduler.tick(0.0)

        self.assertEqual([scheduler.pop_ready(0.0), scheduler.pop_ready(0.33), scheduler.pop_ready(0.66), scheduler.pop_ready(0.99)], ["6", "5", "6", "V"])
        self.assertNotIn("2", scheduler.queue)
