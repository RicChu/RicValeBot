import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.app import AutomationApp
from screen_automation.combat import CombatController, CrowdSkillGroup
from screen_automation.config import CenterROIConfig
from screen_automation.detector import DetectionResult
from screen_automation.login_recovery import LoginAction
from screen_automation.town_teleport import TeleportAction
from screen_automation.window import WindowInfo


def make_app(result: DetectionResult | None) -> AutomationApp:
    app = object.__new__(AutomationApp)
    app.config = SimpleNamespace(
        target_window_title="Target",
        action=SimpleNamespace(dry_run=True, repeat_interval_ms=20, key="3", key_hold_ms=0),
        pointer=SimpleNamespace(offset_y=-20),
        runtime=SimpleNamespace(save_debug_frame=False, poll_interval_ms=20),
        detection=SimpleNamespace(threshold=0.88, center_roi=CenterROIConfig(False, 700, 500, 50)),
        center_target=SimpleNamespace(enabled=False, radius_px=250, key="2", repeat_interval_ms=500),
        crowd_combat=SimpleNamespace(enabled=True, keys=("F2", "F3", "F4"), min_targets=3, skill_cooldown_ms=6000, skill_interval_ms=330, movement_resume_delay_ms=1000),
        walking=SimpleNamespace(speed_px_per_sec=400),
    )
    app.detector = SimpleNamespace(detect=lambda _: result)
    app.negative_detector = SimpleNamespace(detect=lambda _: None)
    app.last_action_at = float("-inf")
    app.last_center_action_at = float("-inf")
    app.was_detected = False
    app.was_task_action_logged = False
    app.was_center_detected = False
    app.walker = None
    app.navigator = None
    app.scheduler = None
    app.next_walk_at = 0.0
    app.hsv_detector = None
    app.combat = CombatController(CrowdSkillGroup(("F2", "F3", "F4"), 3, 6.0, 0.33))
    app.movement_input = SimpleNamespace(
        set_movement=lambda *_: None,
        release=lambda *_: None,
    )
    app.skill_input = SimpleNamespace(
        queue_tap=lambda *_1, **_2: None,
        process=lambda *_: None,
        clear=lambda: None,
    )
    app.capture = lambda _: np.zeros((100, 100, 3), dtype=np.uint8)
    app.annotate = lambda *_: None
    return app


class AppLoggingTests(unittest.TestCase):
    def test_teleport_key_action_pauses_existing_inputs_before_pressing_b(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        movement_calls: list[tuple[int, tuple[str, ...]]] = []
        clear_calls: list[bool] = []
        app.movement_input = SimpleNamespace(set_movement=lambda hwnd, keys: movement_calls.append((hwnd, keys)), release=lambda *_: None)
        app.skill_input = SimpleNamespace(clear=lambda: clear_calls.append(True))
        window = WindowInfo(hwnd=7, title="Target", left=300, top=400, width=500, height=400)

        with patch("screen_automation.app.post_key") as post_key:
            app._handle_teleport_action(window, TeleportAction("key", "open_inventory", key="B"))

        self.assertEqual(movement_calls, [(7, ())])
        self.assertEqual(clear_calls, [True])
        post_key.assert_called_once_with(7, "B", 0)

    def test_teleport_double_click_uses_window_relative_position(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        app.movement_input = SimpleNamespace(set_movement=lambda *_: None, release=lambda *_: None)
        app.skill_input = SimpleNamespace(clear=lambda: None)
        window = WindowInfo(hwnd=7, title="Target", left=300, top=400, width=500, height=400)

        with patch("screen_automation.app.double_click_screen_position") as double_click:
            app._handle_teleport_action(window, TeleportAction("double_click", "waystone", 100, 200))

        double_click.assert_called_once_with((400, 600))

    def test_login_action_releases_movement_clears_skills_and_clicks(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        movement_calls: list[tuple[int, tuple[str, ...]]] = []
        clear_calls: list[bool] = []
        app.movement_input = SimpleNamespace(
            set_movement=lambda hwnd, keys: movement_calls.append((hwnd, keys)),
            release=lambda *_: None,
        )
        app.skill_input = SimpleNamespace(clear=lambda: clear_calls.append(True))
        window = WindowInfo(hwnd=7, title="Target", left=300, top=400, width=500, height=400)

        with patch("screen_automation.app.click_screen_position") as click:
            app._handle_login_action(window, LoginAction("server", "connect", 100, 200))

        self.assertEqual(movement_calls, [(7, ())])
        self.assertEqual(clear_calls, [True])
        click.assert_called_once_with((400, 600))

    def test_does_not_log_when_image_is_not_detected(self) -> None:
        app = make_app(None)
        window = WindowInfo(hwnd=1, title="Target", left=100, top=200, width=500, height=400)

        with patch("screen_automation.app.find_window", return_value=window), patch("screen_automation.app.logging.info") as info:
            app.run(once=True)

        info.assert_not_called()

    def test_does_not_log_a_dry_run_detection_as_a_successful_action(self) -> None:
        app = make_app(DetectionResult(score=0.95, left=30, top=40, width=20, height=10))
        window = WindowInfo(hwnd=1, title="Target", left=100, top=200, width=500, height=400)

        with patch("screen_automation.app.find_window", return_value=window), patch("screen_automation.app.logging.info") as info:
            app.run(once=True)

        info.assert_not_called()

    def test_skips_task_when_negative_example_is_detected(self) -> None:
        app = make_app(DetectionResult(score=0.95, left=30, top=40, width=20, height=10))
        app.negative_detector = SimpleNamespace(detect=lambda _: DetectionResult(score=0.99, left=0, top=0, width=10, height=10))
        window = WindowInfo(hwnd=1, title="Target", left=100, top=200, width=500, height=400)

        with patch("screen_automation.app.find_window", return_value=window), patch("screen_automation.app.logging.info") as info:
            app.run(once=True)

        info.assert_not_called()
        self.assertEqual(app.last_action_at, float("-inf"))

    def test_runs_task_one_and_queues_key_2_for_hsv_target_inside_screen_center(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        app.config.center_target.enabled = True
        app.detector = None
        app.hsv_detector = SimpleNamespace(detect_all=lambda _: (DetectionResult(score=0.9, left=130, top=160, width=20, height=20),))
        pressed: list[str] = []
        app.skill_input = SimpleNamespace(
            queue_tap=lambda key, **_: pressed.append(key),
            process=lambda *_: None,
            clear=lambda: None,
        )
        window = WindowInfo(hwnd=1, title="Target", left=800, top=400, width=500, height=400)

        with (
            patch("screen_automation.app.find_window", return_value=window),
            patch("screen_automation.app.win32api.GetSystemMetrics", side_effect=[1920, 1080]),
            patch("screen_automation.app.move_cursor_to_image") as move_cursor,
        ):
            app.run(once=True)

        self.assertCountEqual(pressed, ["2", "3"])
        move_cursor.assert_called_once()

    def test_queues_key_2_for_target_at_game_window_center_when_window_is_off_desktop_center(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        app.config.center_target.enabled = True
        app.detector = None
        app.hsv_detector = SimpleNamespace(detect_all=lambda _: (DetectionResult(score=0.9, left=240, top=190, width=20, height=20),))
        pressed: list[str] = []
        app.skill_input = SimpleNamespace(
            queue_tap=lambda key, **_: pressed.append(key),
            process=lambda *_: None,
            clear=lambda: None,
        )
        window = WindowInfo(hwnd=1, title="Target", left=100, top=50, width=500, height=400)

        with patch("screen_automation.app.find_window", return_value=window), patch("screen_automation.app.move_cursor_to_image"):
            app.run(once=True)

        self.assertIn("2", pressed)

    def test_logs_center_skill_only_when_key_is_queued(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        queued: list[str] = []
        app.skill_input = SimpleNamespace(queue_tap=lambda key, **_: queued.append(key))

        with patch("screen_automation.app.logging.info") as info:
            app._handle_center_target(10.0, (500, 300))

        self.assertEqual(queued, ["2"])
        self.assertTrue(any("Center skill action" in str(call) for call in info.call_args_list))

    def test_crowd_combat_steers_away_uses_nearest_target_and_queues_first_group_skill(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        app.detector = None
        excluded: list[tuple[str, ...]] = []
        app.walker = SimpleNamespace(next_step=lambda excluded_keys=(): (excluded.append(excluded_keys) or (("A",), 10)))
        app.hsv_detector = SimpleNamespace(
            detect_all=lambda _: (
                DetectionResult(score=0.8, left=5, top=5, width=80, height=15),
                DetectionResult(score=0.8, left=35, top=35, width=80, height=15),
                DetectionResult(score=0.8, left=70, top=70, width=80, height=15),
            )
        )
        pressed: list[str] = []
        movements: list[tuple[str, ...]] = []
        app.movement_input = SimpleNamespace(
            set_movement=lambda _, keys: movements.append(keys),
            release=lambda *_: None,
        )
        app.skill_input = SimpleNamespace(
            queue_tap=lambda key, **_: pressed.append(key),
            process=lambda *_: None,
            clear=lambda: None,
        )
        window = WindowInfo(hwnd=1, title="Target", left=0, top=0, width=100, height=100)

        with patch("screen_automation.app.find_window", return_value=window), patch("screen_automation.app.move_cursor_to_image") as move_cursor, patch("screen_automation.app.logging.info") as info:
            app.run(once=True)

        self.assertEqual(movements[-1], ("A",))
        self.assertEqual(excluded, [("D", "W")])
        self.assertIn("F2", pressed)
        self.assertIn("3", pressed)
        self.assertEqual(move_cursor.call_args.args[1].left, 35)
        self.assertTrue(any("Crowd skill action" in str(call) for call in info.call_args_list))
        self.assertTrue(any("Crowd avoidance" in str(call) for call in info.call_args_list))

    def test_crowd_skill_queue_does_not_replace_active_random_movement(self) -> None:
        app = make_app(None)
        app.config.action.dry_run = False
        app.detector = None
        app.walker = SimpleNamespace(next_step=lambda excluded_keys=(): (("A",), 10))
        app.hsv_detector = SimpleNamespace(
            detect_all=lambda _: (
                DetectionResult(score=0.8, left=5, top=5, width=80, height=15),
                DetectionResult(score=0.8, left=35, top=35, width=80, height=15),
                DetectionResult(score=0.8, left=70, top=70, width=80, height=15),
            )
        )
        movements: list[tuple[str, ...]] = []
        skills: list[str] = []
        app.movement_input = SimpleNamespace(set_movement=lambda _, keys: movements.append(keys), release=lambda *_: None)
        app.skill_input = SimpleNamespace(queue_tap=lambda key, **_: skills.append(key), process=lambda *_: None, clear=lambda: None)
        window = WindowInfo(hwnd=1, title="Target", left=0, top=0, width=100, height=100)

        with patch("screen_automation.app.find_window", return_value=window), patch("screen_automation.app.move_cursor_to_image"):
            app.run(once=True)

        self.assertEqual(movements, [("A",)])
        self.assertIn("F2", skills)


if __name__ == "__main__":
    unittest.main()
