import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.config import SkillConfig, load_config


class ConfigTests(unittest.TestCase):
    def test_reads_active_map_profile(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
active_map: night_garden
maps:
  demon_mouth:
    teleport_template_path: assets/teleport/maps/demon_mouth.png
    target_template_paths: []
    movement_script_path: maps/demon_mouth/movement.yaml
  night_garden:
    teleport_template_path: assets/teleport/maps/night_garden.png
    target_template_paths: [assets/target/maps/night_garden]
    movement_script_path: maps/night_garden/movement.yaml
    arrival_minimap_template_path: assets/teleport/arrival_maps/night_garden.png
    arrival_minimap_threshold: 0.73
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertEqual(config.active_map.name, "night_garden")
        self.assertEqual(config.active_map.teleport_template_path, "assets/teleport/maps/night_garden.png")
        self.assertEqual(config.active_map.target_template_paths, ("assets/target/maps/night_garden",))
        self.assertEqual(config.active_map.movement_script_path, "maps/night_garden/movement.yaml")
        self.assertEqual(config.active_map.arrival_minimap_template_path, "assets/teleport/arrival_maps/night_garden.png")
        self.assertEqual(config.active_map.arrival_minimap_threshold, 0.73)
        self.assertEqual(config.town_teleport.destination.name, "night_garden")
        self.assertEqual(config.town_teleport.destination.template_path, "assets/teleport/maps/night_garden.png")

    def test_uses_default_paths_for_an_empty_map_profile(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
active_map: goblin_warcamp
maps:
  goblin_warcamp: {}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertEqual(config.active_map.teleport_template_path, "assets/maps/goblin_warcamp/teleport.png")
        self.assertEqual(config.active_map.target_template_paths, ("assets/maps/goblin_warcamp/target",))
        self.assertEqual(config.active_map.movement_script_path, "assets/maps/goblin_warcamp/movement.yaml")
        self.assertEqual(config.active_map.arrival_minimap_template_path, "assets/maps/goblin_warcamp/arrival_minimap.png")

    def test_empty_target_template_paths_uses_map_target_directory(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
active_map: fairly_glen
maps:
  fairly_glen:
    target_template_paths: []
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertEqual(config.active_map.target_template_paths, ("assets/maps/fairly_glen/target",))

    def test_rejects_unknown_active_map(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
active_map: absent_map
maps: {}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "active_map"):
                load_config(path)

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
        self.assertEqual(config.action.skills, (SkillConfig("3", 20),))
        self.assertEqual(config.action.skill_interval_ms, 20)
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
        self.assertTrue(config.crowd_combat.keys)
        self.assertEqual(tuple(skill.key for skill in config.crowd_combat.skills), config.crowd_combat.keys)
        self.assertTrue(all(skill.cooldown_ms > 0 for skill in config.crowd_combat.skills))
        self.assertEqual(config.runtime.detection_timing_log_interval_ms, 5000)
        self.assertIn(config.runtime.log_mode, {"off", "events", "diagnostic"})

    def test_reads_route_start_delay(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
active_map: test
maps:
  test:
    teleport_template_path: assets/teleport/maps/test.png
    target_template_paths: []
    movement_script_path: maps/test/movement.yaml
    arrival_minimap_template_path: assets/teleport/arrival_maps/test.png
    route_start_delay_ms: 2500
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertEqual(config.active_map.route_start_delay_ms, 2500)

    def test_reads_multiple_center_skills_with_individual_cooldowns(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action:
  key: '3'
  dry_run: true
  key_hold_ms: 0
  repeat_interval_ms: 20
  skill_interval_ms: 100
  skills: [{key: '3', cooldown_ms: 1000}, {key: '4', cooldown_ms: 2000}]
pointer: {offset_y: -50}
center_target:
  template_paths: []
  radius_px: 250
  key: '2'
  key_hold_ms: 0
  repeat_interval_ms: 500
  skill_interval_ms: 330
  skills: [{key: '2', cooldown_ms: 1000}, {key: '3', cooldown_ms: 2000}]
crowd_combat:
  enabled: true
  keys: [F2, F3]
  min_targets: 3
  skill_cooldown_ms: 6000
  skill_interval_ms: 330
  skills: [{key: F2, cooldown_ms: 6000}, {key: F3, cooldown_ms: 8000}]
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertEqual(config.action.skills, (SkillConfig("3", 1000), SkillConfig("4", 2000)))
        self.assertEqual(config.action.skill_interval_ms, 100)
        self.assertEqual(config.center_target.skills, (SkillConfig("2", 1000), SkillConfig("3", 2000)))
        self.assertEqual(config.center_target.skill_interval_ms, 330)
        self.assertEqual(config.crowd_combat.skills, (SkillConfig("F2", 6000), SkillConfig("F3", 8000)))

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

    def test_rejects_removed_recorded_route_configuration(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
walking:
  enabled: true
  mode: random
  recorded_route:
    enabled: true
    manifest_path: obsolete/manifest.yaml
    min_match_count: 8
    max_position_jump_px: 80
    localization_interval_ms: 250
    waypoint_spacing_px: 20
    arrival_radius_px: 15
    movement_deadzone_px: 4
    stuck_timeout_ms: 1000
    max_retries: 2
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "recorded_route"):
                load_config(path)

    def test_reads_login_recovery_configuration(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
login_recovery:
  enabled: true
  threshold: 0.82
  action_delay_ms: 700
  server:
    name: SEA
    template_path: assets/login/server/sea.png
    connect_template_path: assets/login/server/connect.png
  character:
    name: 滴滴殺手
    template_path: assets/login/character/didi_killer.png
    play_template_path: assets/login/character/play.png
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertTrue(config.login_recovery.enabled)
        self.assertEqual(config.login_recovery.server.name, "SEA")
        self.assertEqual(config.login_recovery.character.name, "滴滴殺手")
        self.assertEqual(config.login_recovery.action_delay_ms, 700)

    def test_reads_town_teleport_configuration(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
town_teleport:
  enabled: true
  threshold: 0.82
  action_delay_ms: 700
  stage_timeout_ms: 8000
  town_minimap_template_path: assets/teleport/city_minimap.png
  town_minimap_roi: [2200, 0, 360, 410]
  consumables_template_path: assets/teleport/consumables.png
  waystone_template_path: assets/teleport/waystone.png
  waystone_confirm_template_path: assets/teleport/waystone_confirm.png
  waystone_confirm_template_paths: [assets/teleport/waystone_confirm.png, assets/teleport/waystone_confirm2.png]
  teleport_confirm_template_path: assets/teleport/teleport_confirm.png
  destination: {name: demon_mouth, template_path: assets/teleport/maps/demon_mouth.png}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertTrue(config.town_teleport.enabled)
        self.assertEqual(config.town_teleport.destination.name, "demon_mouth")
        self.assertEqual(config.town_teleport.stage_timeout_ms, 8000)
        self.assertEqual(config.town_teleport.town_minimap_roi, (2200, 0, 360, 410))
        self.assertEqual(config.town_teleport.teleport_confirm_template_path, "assets/teleport/teleport_confirm.png")
        self.assertEqual(
            config.town_teleport.waystone_confirm_template_paths,
            ("assets/teleport/waystone_confirm.png", "assets/teleport/waystone_confirm2.png"),
        )

    def test_reads_minimap_zoom_configuration(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
minimap_zoom: {enabled: true, town_scroll_steps: 30, combat_scroll_steps: 30, combat_load_wait_ms: 5000, interval_ms: 10}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertTrue(config.minimap_zoom.enabled)
        self.assertEqual((config.minimap_zoom.town_scroll_steps, config.minimap_zoom.combat_scroll_steps), (30, 30))
        self.assertEqual(config.minimap_zoom.combat_load_wait_ms, 5000)

    def test_defaults_active_map_arrival_minimap_to_disabled(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertIsNone(config.active_map.arrival_minimap_template_path)

    def test_rejects_removed_combat_state_configuration(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
combat_state: {enabled: true, template_path: assets/combat/battle_state.png, threshold: 0.85, absence_timeout_ms: 10000, key: '4', roi: [0, 0, 500, 350]}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "combat_state has been removed"):
                load_config(path)

    def test_reads_one_shot_combat_start_skill_sequence(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
combat_start:
  enabled: true
  skill_interval_ms: 330
  verify_delay_ms: 500
  status_template_path: assets/combat/combat_state_icon.png
  status_threshold: 0.85
  status_roi: [0, 0, 500, 350]
  skills: [{key: '4'}, {key: 'F2'}]
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertTrue(config.combat_start.enabled)
        self.assertEqual(config.combat_start.skills, ("4", "F2"))
        self.assertEqual((config.combat_start.skill_interval_ms, config.combat_start.verify_delay_ms), (330, 500))
        self.assertEqual(config.combat_start.status_roi, (0, 0, 500, 350))

    def test_reads_death_recovery_configuration(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
death_recovery:
  enabled: true
  threshold: 0.82
  town_respawn_template_path: assets/death/town_respawn.png
  healer_enabled: true
  healer_template_path: assets/death/healer.png
  healer_dialog_template_path: assets/death/healer_dialog.png
  healer_threshold: 0.80
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertTrue(config.death_recovery.enabled)
        self.assertEqual(config.death_recovery.town_respawn_template_path, "assets/death/town_respawn.png")
        self.assertEqual(config.death_recovery.healer_template_path, "assets/death/healer.png")
        self.assertEqual(config.death_recovery.healer_dialog_template_path, "assets/death/healer_dialog.png")
        self.assertEqual(config.death_recovery.healer_threshold, 0.80)
        self.assertTrue(config.death_recovery.healer_enabled)

    def test_reads_disconnect_recovery_configuration(self) -> None:
        content = """
target_window_title: Target
capture: {method: mss, fallback_to_desktop: true}
detection: {template_paths: [], negative_template_paths: [], threshold: 0.5, roi: null}
action: {key: '3', dry_run: true, key_hold_ms: 0, repeat_interval_ms: 20}
pointer: {offset_y: -50}
center_target: {template_paths: [], radius_px: 250, key: '2', key_hold_ms: 0, repeat_interval_ms: 500}
runtime: {poll_interval_ms: 20, save_debug_frame: false, debug_frame_path: debug/latest_detection.png}
disconnect_recovery: {enabled: true, threshold: 0.79, confirm_template_path: assets/disconnect/confirm.png}
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.yaml"
            path.write_text(content, encoding="utf-8")
            config = load_config(path)

        self.assertTrue(config.disconnect_recovery.enabled)
        self.assertEqual(config.disconnect_recovery.threshold, 0.79)
        self.assertEqual(config.disconnect_recovery.confirm_template_path, "assets/disconnect/confirm.png")


if __name__ == "__main__":
    unittest.main()
