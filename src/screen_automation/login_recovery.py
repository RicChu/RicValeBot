from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from .detector import DetectionResult, TemplateDetector


class Detector(Protocol):
    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None: ...


@dataclass(frozen=True)
class LoginAction:
    stage: str
    label: str
    x: int
    y: int


class LoginRecoveryController:
    """Produces one safe, template-backed login click at a time."""

    def __init__(
        self,
        config: object,
        detector_factory: Callable[[str, float], Detector] | None = None,
        base_dir: Path | None = None,
    ) -> None:
        self.config = config
        self._factory = detector_factory
        self._base_dir = base_dir
        self.server_target = self._make_detector(config.server.template_path)
        self.server_connect = self._make_detector(config.server.connect_template_path)
        self.character_target = self._make_detector(config.character.template_path)
        self.character_play = self._make_detector(config.character.play_template_path)
        self._active_stage: str | None = None
        self._phase = "select"
        self._last_click_at = float("-inf")

    @property
    def active(self) -> bool:
        return self._active_stage is not None

    def reset(self) -> None:
        self._active_stage = None
        self._phase = "select"
        self._last_click_at = float("-inf")

    def _make_detector(self, path: str) -> Detector:
        if self._factory is not None:
            return self._factory(path, self.config.threshold)
        resolved_path = self._base_dir / path if self._base_dir else Path(path)
        return TemplateDetector(resolved_path, self.config.threshold, None)

    @staticmethod
    def _action(stage: str, label: str, match: DetectionResult) -> LoginAction:
        return LoginAction(
            stage=stage,
            label=label,
            x=match.left + match.width // 2,
            y=match.top + match.height // 2,
        )

    def _next_action(
        self,
        stage: str,
        target_label: str,
        target_match: DetectionResult | None,
        second_label: str,
        second_match: DetectionResult,
        now: float,
    ) -> LoginAction | None:
        if self._active_stage != stage:
            self._active_stage = stage
            self._phase = "select"

        if self._phase == "select":
            if target_match is None:
                return None
            self._phase = "continue"
            self._last_click_at = now
            return self._action(stage, target_label, target_match)

        if self._phase == "continue":
            if now - self._last_click_at < self.config.action_delay_ms / 1000:
                return None
            self._phase = "await_transition"
            self._last_click_at = now
            return self._action(stage, second_label, second_match)

        return None

    def handle(self, frame_bgr: np.ndarray, now: float) -> LoginAction | None:
        if not self.config.enabled:
            return None
        if connect_match := self.server_connect.detect(frame_bgr):
            return self._next_action(
                "server",
                f"server:{self.config.server.name}",
                self.server_target.detect(frame_bgr),
                "connect",
                connect_match,
                now,
            )
        if play_match := self.character_play.detect(frame_bgr):
            return self._next_action(
                "character",
                f"character:{self.config.character.name}",
                self.character_target.detect(frame_bgr),
                "play",
                play_match,
                now,
            )
        self._active_stage = None
        self._phase = "select"
        return None
