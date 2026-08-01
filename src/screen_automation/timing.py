from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionTimingReport:
    sample_count: int
    mean_interval_ms: float
    max_interval_ms: float
    over_target_count: int
    mean_capture_ms: float
    mean_detection_ms: float
    mean_action_ms: float


class DetectionTimingMonitor:
    def __init__(self, target_interval_ms: int, report_interval_ms: int) -> None:
        self.target_interval_ms = target_interval_ms
        self.report_interval_ms = report_interval_ms
        self._last_started_at: float | None = None
        self._last_report_at: float | None = None
        self._intervals_ms: list[float] = []
        self._capture_ms: list[float] = []
        self._detection_ms: list[float] = []
        self._action_ms: list[float] = []

    def record(
        self, started_at: float, capture_ms: float = 0.0, detection_ms: float = 0.0, action_ms: float = 0.0
    ) -> DetectionTimingReport | None:
        if self._last_started_at is not None:
            self._intervals_ms.append((started_at - self._last_started_at) * 1000)
            self._capture_ms.append(capture_ms)
            self._detection_ms.append(detection_ms)
            self._action_ms.append(action_ms)
        self._last_started_at = started_at
        if self.report_interval_ms <= 0:
            self._intervals_ms.clear()
            self._capture_ms.clear()
            self._detection_ms.clear()
            self._action_ms.clear()
            return None
        if self._last_report_at is None:
            self._last_report_at = started_at
            return None
        if started_at - self._last_report_at < self.report_interval_ms / 1000 or not self._intervals_ms:
            return None
        report = DetectionTimingReport(
            sample_count=len(self._intervals_ms),
            mean_interval_ms=sum(self._intervals_ms) / len(self._intervals_ms),
            max_interval_ms=max(self._intervals_ms),
            over_target_count=sum(interval > self.target_interval_ms for interval in self._intervals_ms),
            mean_capture_ms=sum(self._capture_ms) / len(self._capture_ms),
            mean_detection_ms=sum(self._detection_ms) / len(self._detection_ms),
            mean_action_ms=sum(self._action_ms) / len(self._action_ms),
        )
        self._intervals_ms.clear()
        self._capture_ms.clear()
        self._detection_ms.clear()
        self._action_ms.clear()
        self._last_report_at = started_at
        return report
