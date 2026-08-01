import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.timing import DetectionTimingMonitor


class DetectionTimingTests(unittest.TestCase):
    def test_reports_capture_intervals_that_exceed_the_twenty_millisecond_target(self) -> None:
        monitor = DetectionTimingMonitor(target_interval_ms=20, report_interval_ms=100)

        self.assertIsNone(monitor.record(0.000, capture_ms=8.0, detection_ms=4.0, action_ms=3.0))
        self.assertIsNone(monitor.record(0.020, capture_ms=12.0, detection_ms=6.0, action_ms=4.0))
        report = monitor.record(0.125, capture_ms=16.0, detection_ms=8.0, action_ms=5.0)

        self.assertIsNotNone(report)
        self.assertEqual(report.sample_count, 2)
        self.assertEqual(report.over_target_count, 1)
        self.assertAlmostEqual(report.mean_interval_ms, 62.5)
        self.assertAlmostEqual(report.max_interval_ms, 105.0)
        self.assertAlmostEqual(report.mean_capture_ms, 14.0)
        self.assertAlmostEqual(report.mean_detection_ms, 7.0)
        self.assertAlmostEqual(report.mean_action_ms, 4.5)


if __name__ == "__main__":
    unittest.main()
