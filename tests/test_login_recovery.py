import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.detector import DetectionResult
from screen_automation.login_recovery import LoginRecoveryController


class FakeDetector:
    def __init__(self, result: DetectionResult | None) -> None:
        self.result = result

    def detect(self, _frame: np.ndarray) -> DetectionResult | None:
        return self.result


def recovery_config() -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        threshold=0.8,
        action_delay_ms=500,
        server=SimpleNamespace(
            name="SEA",
            template_path="server.png",
            connect_template_path="connect.png",
        ),
        character=SimpleNamespace(
            name="滴滴殺手",
            template_path="character.png",
            play_template_path="play.png",
        ),
    )


class LoginRecoveryControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)

    def test_server_stage_selects_configured_server_before_connecting(self) -> None:
        matches = {
            "connect.png": DetectionResult(0.95, 70, 80, 20, 10),
            "server.png": DetectionResult(0.91, 10, 20, 30, 10),
            "play.png": None,
            "character.png": None,
        }
        controller = LoginRecoveryController(recovery_config(), lambda path, _threshold: FakeDetector(matches[path]))

        select_server = controller.handle(self.frame, now=0.0)
        connect = controller.handle(self.frame, now=0.5)

        self.assertEqual((select_server.stage, select_server.label, select_server.x, select_server.y), ("server", "server:SEA", 25, 25))
        self.assertEqual((connect.stage, connect.label, connect.x, connect.y), ("server", "connect", 80, 85))

    def test_character_stage_selects_configured_character_before_playing(self) -> None:
        matches = {
            "connect.png": None,
            "server.png": None,
            "play.png": DetectionResult(0.95, 70, 80, 20, 10),
            "character.png": DetectionResult(0.91, 10, 20, 30, 10),
        }
        controller = LoginRecoveryController(recovery_config(), lambda path, _threshold: FakeDetector(matches[path]))

        select_character = controller.handle(self.frame, now=0.0)
        play = controller.handle(self.frame, now=0.5)

        self.assertEqual((select_character.stage, select_character.label, select_character.x, select_character.y), ("character", "character:滴滴殺手", 25, 25))
        self.assertEqual((play.stage, play.label, play.x, play.y), ("character", "play", 80, 85))

    def test_unknown_frame_returns_no_action(self) -> None:
        controller = LoginRecoveryController(recovery_config(), lambda _path, _threshold: FakeDetector(None))

        self.assertIsNone(controller.handle(self.frame, now=0.0))

    def test_waits_for_configured_delay_before_second_click(self) -> None:
        matches = {
            "connect.png": DetectionResult(0.95, 70, 80, 20, 10),
            "server.png": DetectionResult(0.91, 10, 20, 30, 10),
            "play.png": None,
            "character.png": None,
        }
        controller = LoginRecoveryController(recovery_config(), lambda path, _threshold: FakeDetector(matches[path]))

        controller.handle(self.frame, now=0.0)

        self.assertIsNone(controller.handle(self.frame, now=0.49))


if __name__ == "__main__":
    unittest.main()
