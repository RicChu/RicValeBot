from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from .detector import DetectionResult, TemplateDetector


class Detector(Protocol):
    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None: ...


@dataclass(frozen=True)
class DeathAction:
    label: str
    x: int
    y: int


class DeathRecoveryController:
    """Respawns in town, then optionally completes the configured healer dialogue."""

    def __init__(
        self,
        config: object,
        detector_factory: Callable[[str, float], Detector] | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self.config = config
        if detector_factory is not None:
            self.respawn = detector_factory(config.town_respawn_template_path, config.threshold)
        else:
            path = base_dir / config.town_respawn_template_path if base_dir else Path(config.town_respawn_template_path)
            self.respawn = TemplateDetector(path, config.threshold, None)
        self.healer = self._make_detector("healer_template_path", "healer_threshold", detector_factory, base_dir)
        self.healer_dialog = self._make_detector("healer_dialog_template_path", "healer_threshold", detector_factory, base_dir)
        self._phase = "idle"

    def _make_detector(
        self,
        path_attribute: str,
        threshold_attribute: str,
        detector_factory: Callable[[str, float], Detector] | None,
        base_dir: Path | None,
    ) -> Detector | None:
        if not getattr(self.config, "healer_enabled", False):
            return None
        path = getattr(self.config, path_attribute)
        threshold = getattr(self.config, threshold_attribute)
        if detector_factory is not None:
            return detector_factory(path, threshold)
        return TemplateDetector((base_dir / path) if base_dir else Path(path), threshold, None)

    @property
    def active(self) -> bool:
        return self._phase != "idle"

    def reset(self) -> None:
        self._phase = "idle"

    def handle(self, frame_bgr: np.ndarray) -> DeathAction | None:
        if not self.config.enabled:
            return None
        if self._phase == "idle":
            match = self.respawn.detect(frame_bgr)
            if match is None:
                return None
            self._phase = "waiting_for_respawn_close"
            return DeathAction("town_respawn", match.left + match.width // 2, match.top + match.height // 2)
        if self._phase == "waiting_for_respawn_close":
            if self.respawn.detect(frame_bgr) is None:
                self._phase = "waiting_for_healer" if self.healer else "idle"
            return None
        if self._phase == "waiting_for_healer":
            match = self.healer.detect(frame_bgr) if self.healer else None
            if match is not None:
                self._phase = "waiting_for_healer_dialog"
                return DeathAction("healer", match.left + match.width // 2, match.top + match.height // 2)
            return None
        if self._phase == "waiting_for_healer_dialog":
            match = self.healer_dialog.detect(frame_bgr) if self.healer_dialog else None
            if match is not None:
                self._phase = "waiting_for_healer_dialog_close"
                return DeathAction("healer_dialog", match.left + match.width // 2, match.top + match.height // 2)
            return None
        if self._phase == "waiting_for_healer_dialog_close" and (self.healer_dialog is None or self.healer_dialog.detect(frame_bgr) is None):
            self.reset()
        return None
