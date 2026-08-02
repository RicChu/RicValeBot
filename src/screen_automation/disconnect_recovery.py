from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from .detector import DetectionResult, TemplateDetector


class Detector(Protocol):
    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None: ...


@dataclass(frozen=True)
class DisconnectAction:
    label: str
    x: int
    y: int


class DisconnectRecoveryController:
    """Confirms a disconnect dialog once, then lets normal login recovery continue."""

    def __init__(
        self,
        config: object,
        detector_factory: Callable[[str, float], Detector] | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self.config = config
        if detector_factory is not None:
            self.confirm = detector_factory(config.confirm_template_path, config.threshold)
        else:
            path = base_dir / config.confirm_template_path if base_dir else Path(config.confirm_template_path)
            self.confirm = TemplateDetector(path, config.threshold, None)
        self._waiting_for_close = False

    @property
    def active(self) -> bool:
        return self._waiting_for_close

    def reset(self) -> None:
        self._waiting_for_close = False

    def handle(self, frame_bgr: np.ndarray) -> DisconnectAction | None:
        if not self.config.enabled:
            return None
        match = self.confirm.detect(frame_bgr)
        if not self._waiting_for_close:
            if match is None:
                return None
            self._waiting_for_close = True
            return DisconnectAction("disconnect_confirm", match.left + match.width // 2, match.top + match.height // 2)
        if match is None:
            self.reset()
        return None
