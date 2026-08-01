import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.config import load_config


class ConfigTests(unittest.TestCase):
    def test_reads_repeat_interval_and_cursor_offset(self) -> None:
        content = """
target_window_title: Target
capture: {method: printwindow, fallback_to_desktop: true}
detection: {template_paths: [assets/target.png, assets/target_secondary.png], negative_template_paths: [assets/negative.png], threshold: 0.88, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 50, repeat_interval_ms: 100}
pointer: {offset_y: -20}
runtime: {poll_interval_ms: 250, save_debug_frame: true, debug_frame_path: debug/latest_detection.png}
center_target: {template_paths: [assets/center_target.png], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 2000}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertEqual(config.action.key, "3")
        self.assertEqual(config.detection.template_paths, ("assets/target.png", "assets/target_secondary.png"))
        self.assertEqual(config.detection.negative_template_paths, ("assets/negative.png",))
        self.assertEqual(config.action.repeat_interval_ms, 100)
        self.assertEqual(config.pointer.offset_y, -20)
        self.assertEqual(config.center_target.radius_px, 250)
        self.assertEqual(config.center_target.key, "2")
        self.assertFalse(config.detection.center_roi.enabled)

    def test_default_task_one_uses_twenty_millisecond_active_detection(self) -> None:
        config = load_config(Path(__file__).parents[1] / "config.yaml")

        self.assertEqual(config.action.key, "3")
        self.assertEqual(config.action.key_hold_ms, 0)
        self.assertEqual(config.action.repeat_interval_ms, 20)
        self.assertEqual(config.runtime.poll_interval_ms, 20)
        self.assertTrue(config.detection.center_roi.enabled)
        self.assertGreater(config.detection.center_roi.width, 0)
        self.assertGreater(config.detection.center_roi.height, 0)
        self.assertEqual(config.hsv_bar.min_height, 8)
        self.assertEqual(config.hsv_bar.max_white_ratio, 0.80)
        self.assertEqual(config.hsv_bar.min_horizontal_run_ratio, 0.50)
        self.assertEqual(config.hsv_bar.min_allowed_colour_ratio, 0.60)
        self.assertTrue(config.hsv_bar.inner_band_enabled)
        self.assertIsInstance(config.hsv_bar.black_residual_enabled, bool)
        self.assertEqual(config.crowd_combat.keys, ("F2", "F3", "F4"))
        self.assertEqual(config.crowd_combat.skill_cooldown_ms, 6000)
        self.assertEqual(config.runtime.detection_timing_log_interval_ms, 5000)
        self.assertIn(config.runtime.log_mode, {"off", "events", "diagnostic"})

    def test_reads_route_walking_mode_and_waypoints(self) -> None:
        content = """
target_window_title: Target
capture: {method: printwindow, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
crowd_combat: {enabled: true, keys: [F2, F3, F4], min_targets: 3, skill_cooldown_ms: 6000, skill_interval_ms: 330}
walking:
  enabled: true
  mode: route
  step_distance: 600
  speed_px_per_sec: 400
  boundary_x: 2000
  boundary_y: 1000
  route:
    minimap: {right_px: 20, top_px: 20, width_px: 330, height_px: 330}
    white_threshold: 220
    pair_max_distance_px: 18
    arrival_radius_px: 12
    movement_deadzone_px: 4
    map_recording: {enabled: true, manifest_path: maps/test/manifest.yaml, min_match_count: 8, max_position_jump_px: 70}
    waypoints: [{name: A, x: 120, y: 90}, {name: B, x: 170, y: 130}]
runtime: {poll_interval_ms: 20, detection_timing_log_interval_ms: 5000, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertEqual(config.walking.mode, "route")
        self.assertEqual(config.walking.route.waypoints[1].name, "B")
        self.assertEqual((config.walking.route.minimap.right_px, config.walking.route.arrival_radius_px), (20, 12))
        self.assertTrue(config.walking.route.map_recording.enabled)
        self.assertEqual(config.walking.route.map_recording.manifest_path, "maps/test/manifest.yaml")
        self.assertEqual(config.crowd_combat.keys, ("F2", "F3", "F4"))
        self.assertEqual(config.crowd_combat.min_targets, 3)


if __name__ == "__main__":
    unittest.main()
