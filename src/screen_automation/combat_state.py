from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from .detector import DetectionResult, TemplateDetector


class Detector(Protocol):
    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None: ...


@dataclass(frozen=True)
class CombatStateAction:
    key: str


class CombatStateController:
    """Requests a recovery key after the battle-state icon has been absent long enough."""

    def __init__(
        self,
        config: object,
        detector_factory: Callable[[str, float], Detector] | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self.config = config
        if detector_factory is not None:
            self.state_icon = detector_factory(config.template_path, config.threshold)
        else:
            path = base_dir / config.template_path if base_dir else Path(config.template_path)
            self.state_icon = TemplateDetector(path, config.threshold, None)
        self._last_seen_at: float | None = None

    def reset(self) -> None:
        self._last_seen_at = None

    def handle(self, frame_bgr: np.ndarray, now: float) -> CombatStateAction | None:
        if not self.config.enabled:
            return None
        left, top, width, height = self.config.roi
        roi = frame_bgr[top : min(top + height, frame_bgr.shape[0]), left : min(left + width, frame_bgr.shape[1])]
        if self.state_icon.detect(roi):
            self._last_seen_at = now
            return None
        if self._last_seen_at is None:
            self._last_seen_at = now
            return None
        if now - self._last_seen_at < self.config.absence_timeout_ms / 1000:
            return None
        self._last_seen_at = now
        return CombatStateAction(self.config.key)
