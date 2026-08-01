from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from .detector import DetectionResult, TemplateDetector


class Detector(Protocol):
    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None: ...


@dataclass(frozen=True)
class TeleportAction:
    kind: str
    label: str
    x: int | None = None
    y: int | None = None
    key: str | None = None


class TownTeleportController:
    """Produces the safe, image-confirmed steps for a town Waystone teleport."""

    def __init__(
        self,
        config: object,
        detector_factory: Callable[[str, float], Detector] | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self.config = config
        self._factory = detector_factory
        self._base_dir = base_dir
        self.town_minimap = self._make_detector(config.town_minimap_template_path, getattr(config, "town_minimap_roi", None))
        self.consumables = self._make_detector(config.consumables_template_path)
        self.waystone = self._make_detector(config.waystone_template_path)
        self.waystone_confirm = self._make_detector(config.waystone_confirm_template_path)
        self.destination = self._make_detector(config.destination.template_path)
        self._phase = "idle"
        self._stage_started_at = float("-inf")
        self._last_action_at = float("-inf")

    @property
    def active(self) -> bool:
        return self._phase != "idle"

    def _make_detector(self, path: str, roi: tuple[int, int, int, int] | None = None) -> Detector:
        if self._factory is not None:
            return self._factory(path, self.config.threshold)
        resolved_path = self._base_dir / path if self._base_dir else Path(path)
        return TemplateDetector(resolved_path, self.config.threshold, roi)

    @staticmethod
    def _click(kind: str, label: str, match: DetectionResult) -> TeleportAction:
        return TeleportAction(kind, label, match.left + match.width // 2, match.top + match.height // 2)

    def _reset(self) -> None:
        self._phase = "idle"
        self._stage_started_at = float("-inf")

    def _advance(self, phase: str, now: float, action: TeleportAction) -> TeleportAction:
        self._phase = phase
        self._stage_started_at = now
        self._last_action_at = now
        return action

    def _ready(self, now: float) -> bool:
        return now - self._last_action_at >= self.config.action_delay_ms / 1000

    def _expired(self, now: float) -> bool:
        return now - self._stage_started_at >= self.config.stage_timeout_ms / 1000

    def handle(self, frame_bgr: np.ndarray, now: float) -> TeleportAction | None:
        if not self.config.enabled:
            return None

        if self._phase == "idle":
            if not self.town_minimap.detect(frame_bgr):
                return None
            return self._advance("consumables", now, TeleportAction("key", "open_inventory", key="B"))

        if self._expired(now):
            self._reset()
            return None
        if not self._ready(now):
            return None

        stages: dict[str, tuple[Detector, str, str, str]] = {
            "consumables": (self.consumables, "click", "consumables", "waystone"),
            "waystone": (self.waystone, "double_click", "waystone", "waystone_confirm"),
            "waystone_confirm": (self.waystone_confirm, "click", "waystone_confirm", "destination"),
            "destination": (self.destination, "click", f"map:{self.config.destination.name}", "await_departure"),
        }
        if self._phase == "await_departure":
            if not self.town_minimap.detect(frame_bgr):
                self._reset()
            return None

        detector, kind, label, next_phase = stages[self._phase]
        if match := detector.detect(frame_bgr):
            return self._advance(next_phase, now, self._click(kind, label, match))
        return None
