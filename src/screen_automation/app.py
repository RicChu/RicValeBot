from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import numpy as np
import win32api

from .capture import ReusableMSSCapture
from .center_target import is_inside_window_center_radius
from .combat import CombatController, CrowdSkillGroup, PrioritySkillGroup, directions_toward_target, select_nearest_to_center, steer_away_from_target
from .combat_start import CombatStartSkillGroup
from .config import AppConfig
from .death_recovery import DeathAction, DeathRecoveryController
from .detector import DetectionResult, MultiTemplateDetector, TemplateDetector
from .disconnect_recovery import DisconnectAction, DisconnectRecoveryController
from .hsv_bar import HSVBarDetector
from .input_coordinator import MovementInput, SkillTapQueue
from .keyboard import post_key
from .login_recovery import LoginAction, LoginRecoveryController
from .map_arrival_wait import MapArrivalWaitController
from .map_localization import MapLocalizer
from .minimap_zoom import MinimapZoomController
from .navigation import RouteNavigator, Waypoint, find_white_pair, minimap_bounds
from .pointer import click_screen_position, ctrl_wheel_at, double_click_screen_position, image_hover_position, move_cursor_to_image
from .roi import center_roi_bounds, translate_detection
from .scripted_route import ScriptedRouteController, load_movement_script
from .skill_queue import SkillScheduler
from .timing import DetectionTimingMonitor, remaining_poll_sleep_seconds
from .town_teleport import TeleportAction, TownTeleportController
from .walking import WalkingController
from .window import WindowInfo, capture_print_window, find_window


def existing_template_paths(base_dir: Path, paths: tuple[str, ...]) -> tuple[Path, ...]:
    """Return only configured template paths that are currently available.

    A map profile may use its default ``targets/`` directory before target
    screenshots have been collected.  That must disable only template fallback,
    not prevent HSV detection or the rest of the automation from starting.
    """
    return tuple(path for relative_path in paths if (path := base_dir / relative_path).exists())


class AutomationApp:
    def __init__(self, config: AppConfig, base_dir: Path) -> None:
        self.config = config
        self.base_dir = base_dir
        self.desktop_capture = ReusableMSSCapture()
        self.detector = (
            MultiTemplateDetector(tuple(base_dir / path for path in config.detection.template_paths), config.detection.threshold, config.detection.roi)
            if config.detection.template_paths else None
        )
        self.negative_detector = (
            MultiTemplateDetector(tuple(base_dir / path for path in config.detection.negative_template_paths), config.detection.threshold, config.detection.roi)
            if config.detection.negative_template_paths else None
        )
        map_target_paths = existing_template_paths(base_dir, config.active_map.target_template_paths)
        self.map_target_detector = (
            MultiTemplateDetector(
                map_target_paths,
                config.detection.threshold,
                config.detection.roi,
            )
            if map_target_paths
            else None
        )
        self.hsv_detector = (
            HSVBarDetector(
                config.hsv_bar.min_width,
                config.hsv_bar.max_height,
                config.hsv_bar.min_aspect_ratio,
                max_width=config.hsv_bar.max_width,
                min_height=config.hsv_bar.min_height,
                max_aspect_ratio=config.hsv_bar.max_aspect_ratio,
                max_white_ratio=config.hsv_bar.max_white_ratio,
                min_horizontal_run_ratio=config.hsv_bar.min_horizontal_run_ratio,
                min_allowed_colour_ratio=config.hsv_bar.min_allowed_colour_ratio,
                edge_band_px=config.hsv_bar.edge_band_px,
                edge_black_ratio=config.hsv_bar.edge_black_ratio,
                inner_band_enabled=config.hsv_bar.inner_band_enabled,
                black_residual_enabled=config.hsv_bar.black_residual_enabled,
                black_residual_min_extent=config.hsv_bar.black_residual.min_extent,
                black_residual_dedup_iou=config.hsv_bar.black_residual.dedup_iou,
                black_residual_outer_ring_px=config.hsv_bar.black_residual.outer_ring_px,
                black_residual_min_outer_contrast=config.hsv_bar.black_residual.min_outer_contrast,
                black_residual_low_colour_trigger_ratio=config.hsv_bar.black_residual.low_colour_trigger_ratio,
            )
            if config.hsv_bar.enabled
            else None
        )
        self.last_action_at = float("-inf")
        self.last_center_action_at = float("-inf")
        self.was_detected = False
        self.was_task_action_logged = False
        self.was_center_detected = False
        self.task_one_skill_group = PrioritySkillGroup(
            tuple((skill.key, skill.cooldown_ms / 1000) for skill in config.action.skills),
            config.action.skill_interval_ms / 1000,
        )
        self.center_skill_group = PrioritySkillGroup(
            tuple((skill.key, skill.cooldown_ms / 1000) for skill in config.center_target.skills),
            config.center_target.skill_interval_ms / 1000,
        )
        self.combat_start_skill_group = CombatStartSkillGroup(
            config.combat_start.skills,
            config.combat_start.skill_interval_ms / 1000,
            config.combat_start.verify_delay_ms / 1000,
        )
        self.combat_start_status_detector = (
            TemplateDetector(
                base_dir / config.combat_start.status_template_path,
                config.combat_start.status_threshold,
                config.combat_start.status_roi,
            )
            if config.combat_start.enabled
            else None
        )
        self.walker = WalkingController(config.walking.step_distance, config.walking.boundary_x, config.walking.boundary_y) if config.walking.enabled and config.walking.mode in {"random", "scripted_route"} else None
        self.navigator = (
            RouteNavigator(
                tuple(Waypoint(point.name, point.x, point.y) for point in config.walking.route.waypoints),
                config.walking.route.arrival_radius_px,
                config.walking.route.movement_deadzone_px,
            )
            if config.walking.enabled and config.walking.mode == "route"
            else None
        )
        self.route_target_name: str | None = None
        self.localizer = (
            MapLocalizer(
                base_dir / config.walking.route.map_recording.manifest_path,
                config.walking.route.map_recording.min_match_count,
                config.walking.route.map_recording.max_position_jump_px,
            )
            if self.navigator and config.walking.route.map_recording.enabled
            else None
        )
        self.scripted_route: ScriptedRouteController | None = None
        self.scripted_route_state: str | None = None
        if config.walking.enabled and config.walking.mode == "scripted_route" and config.active_map.movement_script_path:
            self.scripted_route = ScriptedRouteController(load_movement_script(base_dir / config.active_map.movement_script_path))
        self.next_walk_at = 0.0
        self.combat = (
            CombatController(
                CrowdSkillGroup(
                    config.crowd_combat.keys,
                    config.crowd_combat.min_targets,
                    config.crowd_combat.skill_cooldown_ms / 1000,
                    config.crowd_combat.skill_interval_ms / 1000,
                    tuple((skill.key, skill.cooldown_ms / 1000) for skill in config.crowd_combat.skills),
                )
            )
            if config.crowd_combat.enabled
            else None
        )
        self.scheduler = SkillScheduler(config.skill_queue.queue_interval_ms, config.skill_queue.schedules) if config.skill_queue.enabled else None
        self.current_hwnd: int | None = None
        self.movement_input = MovementInput()
        self.skill_input = SkillTapQueue(20)
        self.timing_monitor = DetectionTimingMonitor(
            config.runtime.poll_interval_ms,
            config.runtime.detection_timing_log_interval_ms,
        )
        self.login_recovery = (
            LoginRecoveryController(config.login_recovery, base_dir=base_dir)
            if config.login_recovery.enabled
            else None
        )
        self.disconnect_recovery = (
            DisconnectRecoveryController(config.disconnect_recovery, base_dir=base_dir)
            if config.disconnect_recovery.enabled
            else None
        )
        self.town_teleport = (
            TownTeleportController(config.town_teleport, base_dir=base_dir)
            if config.town_teleport.enabled
            else None
        )
        self.minimap_zoom = MinimapZoomController(
            config.minimap_zoom.enabled,
            config.minimap_zoom.town_scroll_steps,
            config.minimap_zoom.combat_scroll_steps,
            config.minimap_zoom.interval_ms,
            config.minimap_zoom.combat_load_wait_ms,
        )
        self._town_minimap_zoomed = not config.minimap_zoom.enabled
        self.map_arrival_wait = (
            MapArrivalWaitController()
            if self.scripted_route and config.active_map.arrival_minimap_template_path
            else None
        )
        self.map_arrival_detector = (
            MultiTemplateDetector(
                (base_dir / config.active_map.arrival_minimap_template_path,),
                config.active_map.arrival_minimap_threshold,
                None,
            )
            if self.map_arrival_wait
            else None
        )
        self.death_recovery = (
            DeathRecoveryController(config.death_recovery, base_dir=base_dir)
            if config.death_recovery.enabled
            else None
        )
    def stop(self) -> None:
        if self.current_hwnd and not self.config.action.dry_run:
            self.movement_input.release(self.current_hwnd)
        self.skill_input.clear()
        self.desktop_capture.close()

    def _sleep_until_next_poll(self, started_at: float) -> None:
        delay = remaining_poll_sleep_seconds(
            self.config.runtime.poll_interval_ms,
            started_at,
            time.monotonic(),
        )
        if delay:
            time.sleep(delay)

    def capture(self, window: WindowInfo) -> np.ndarray:
        try:
            if self.config.capture.method == "printwindow":
                return capture_print_window(window)
        except RuntimeError as error:
            if not self.config.capture.fallback_to_desktop:
                raise
            logging.warning("PrintWindow capture failed; using desktop capture: %s", error)
        shot = self.desktop_capture.grab({"left": window.left, "top": window.top, "width": window.width, "height": window.height})
        # MSS yields BGRA. OpenCV's colour conversions accept it directly, so
        # retaining the native buffer avoids a full-frame BGR copy each cycle.
        return np.asarray(shot)

    def annotate(self, frame: np.ndarray, detection: DetectionResult) -> None:
        cv2.rectangle(frame, (detection.left, detection.top), (detection.left + detection.width, detection.top + detection.height), (0, 255, 0), 2)
        cv2.putText(frame, f"score={detection.score:.3f}", (detection.left, max(18, detection.top - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def _is_center_hsv_target(self, window: WindowInfo, detection: DetectionResult) -> bool:
        return self.config.center_target.enabled and is_inside_window_center_radius(window, detection, self.config.center_target.radius_px)

    def _handle_center_target(self, now: float, image_position: tuple[int, int]) -> None:
        key = self.center_skill_group.next_skill(now)
        if key:
            if not self.config.action.dry_run:
                self.skill_input.queue_tap(key, coalesce=True)
                logging.info("Center skill action; screen position=%s; key=%s", image_position, key)
            self.last_center_action_at = now
        self.was_center_detected = True
        self.was_task_action_logged = False

    def _handle_task_one(self, window: WindowInfo, detection: DetectionResult, cursor_position: tuple[int, int], now: float) -> None:
        self.was_center_detected = False
        # Pointer tracking is intentionally independent from skill cooldowns.
        # The bar can move before Task 1 is ready to emit its next key.
        if not self.config.action.dry_run:
            move_cursor_to_image(window, detection, self.config.pointer.offset_y)
        key = self.task_one_skill_group.next_skill(now)
        if key is None:
            return
        if not self.config.action.dry_run:
            self.skill_input.queue_tap(key, coalesce=True)
            if not self.was_task_action_logged:
                logging.info("Task 1 action; cursor target=%s; cursor=%s; key=%s", cursor_position, win32api.GetCursorPos(), key)
                self.was_task_action_logged = True
        self.last_action_at = now

    def _pause_for_login(self, window: WindowInfo) -> None:
        self.skill_input.clear()
        if not self.config.action.dry_run:
            self.movement_input.set_movement(window.hwnd, ())

    def _handle_login_action(self, window: WindowInfo, action: LoginAction) -> None:
        self._pause_for_login(window)
        if self.config.action.dry_run:
            return
        position = (window.left + action.x, window.top + action.y)
        click_screen_position(position)
        logging.info("Login recovery action; stage=%s; action=%s; position=%s", action.stage, action.label, position)

    def _handle_teleport_action(self, window: WindowInfo, action: TeleportAction) -> None:
        self._pause_for_login(window)
        if self.config.action.dry_run:
            return
        if action.kind == "key":
            post_key(window.hwnd, action.key or "", 0)
            logging.info("Town teleport action; action=%s; key=%s", action.label, action.key)
            return
        if action.x is None or action.y is None:
            raise ValueError("Teleport click action requires a position")
        position = (window.left + action.x, window.top + action.y)
        if action.kind == "double_click":
            double_click_screen_position(position)
        elif action.kind == "click":
            click_screen_position(position)
        else:
            raise ValueError(f"Unsupported teleport action: {action.kind}")
        logging.info("Town teleport action; action=%s; position=%s", action.label, position)

    def _handle_death_action(self, window: WindowInfo, action: DeathAction) -> None:
        if login_recovery := getattr(self, "login_recovery", None):
            login_recovery.reset()
        if town_teleport := getattr(self, "town_teleport", None):
            town_teleport.reset()
        self._cancel_minimap_zoom()
        self._cancel_route_playback()
        self._trigger_combat_start("death_recovery", time.monotonic())
        self._pause_for_login(window)
        if self.config.action.dry_run:
            return
        position = (window.left + action.x, window.top + action.y)
        click_screen_position(position)
        logging.info("Death recovery action; action=%s; position=%s", action.label, position)

    def _handle_disconnect_action(self, window: WindowInfo, action: DisconnectAction) -> None:
        if login_recovery := getattr(self, "login_recovery", None):
            login_recovery.reset()
        if town_teleport := getattr(self, "town_teleport", None):
            town_teleport.reset()
        self._cancel_minimap_zoom()
        self._cancel_route_playback()
        self._trigger_combat_start("disconnect_recovery", time.monotonic())
        self._pause_for_login(window)
        if self.config.action.dry_run:
            return
        position = (window.left + action.x, window.top + action.y)
        click_screen_position(position)
        logging.info("Disconnect recovery action; action=%s; position=%s", action.label, position)

    def _cancel_route_playback(self) -> None:
        if scripted_route := getattr(self, "scripted_route", None):
            scripted_route.cancel()
        if map_arrival_wait := getattr(self, "map_arrival_wait", None):
            map_arrival_wait.cancel()

    def _trigger_combat_start(self, reason: str, now: float) -> None:
        combat_start_config = getattr(self.config, "combat_start", None)
        combat_start_skill_group = getattr(self, "combat_start_skill_group", None)
        if (
            combat_start_config is None
            or combat_start_skill_group is None
            or not combat_start_config.enabled
        ):
            return
        combat_start_skill_group.trigger(reason, now)
        logging.info("Combat start verification requested; reason=%s", reason)

    def _handle_combat_start(self, frame: np.ndarray, now: float) -> None:
        combat_start_skill_group = getattr(self, "combat_start_skill_group", None)
        status_detector = getattr(self, "combat_start_status_detector", None)
        if combat_start_skill_group is None or status_detector is None or not combat_start_skill_group.active:
            return
        status_visible = status_detector.detect(frame) is not None
        was_active = combat_start_skill_group.active
        key = combat_start_skill_group.next_skill(status_visible, now)
        if was_active and not combat_start_skill_group.active:
            logging.info("Combat start verification confirmed; status icon is visible")
            return
        if key is None or self.config.action.dry_run:
            return
        self.skill_input.queue_tap(key, coalesce=True)
        logging.info("Combat start action; status_visible=%s; key=%s", status_visible, key)

    def _cancel_minimap_zoom(self) -> None:
        if minimap_zoom := getattr(self, "minimap_zoom", None):
            minimap_zoom.cancel()
        self._town_minimap_zoomed = False

    def _handle_teleport_departure(self, now: float) -> None:
        self._trigger_combat_start("town_teleport", now)
        if scripted_route := getattr(self, "scripted_route", None):
            if map_arrival_wait := getattr(self, "map_arrival_wait", None):
                map_arrival_wait.start()
                logging.info("Map arrival wait started; map=%s", self.config.active_map.name)
                return
            scripted_route.start(now)
            self.scripted_route_state = None
            logging.info("Scripted route started")
            return

    def _run_map_arrival_wait(self, window: WindowInfo, frame: np.ndarray, now: float) -> bool:
        map_arrival_wait = getattr(self, "map_arrival_wait", None)
        if map_arrival_wait is None or not map_arrival_wait.active:
            return False
        arrival_visible = bool(self.map_arrival_detector and self.map_arrival_detector.detect(frame))
        route_start_delay_seconds = getattr(self.config.active_map, "route_start_delay_ms", 0) / 1000
        was_waiting_for_arrival = map_arrival_wait.state == "waiting_for_arrival"
        still_waiting = map_arrival_wait.observe(arrival_visible, now, route_start_delay_seconds)
        if was_waiting_for_arrival and map_arrival_wait.state == "waiting_before_route":
            logging.info(
                "Map arrival detected; waiting before scripted route; map=%s; delay_ms=%s",
                self.config.active_map.name,
                getattr(self.config.active_map, "route_start_delay_ms", 0),
            )
        if not self.config.action.dry_run:
            self.movement_input.set_movement(window.hwnd, ())
        if not still_waiting and (scripted_route := getattr(self, "scripted_route", None)):
            scripted_route.start(now)
            self.scripted_route_state = None
            logging.info("Map arrival ready; scripted route started; map=%s", self.config.active_map.name)
        return still_waiting

    def _handle_minimap_zoom_completion(self, phase: str, now: float) -> None:
        if phase == "town":
            self._town_minimap_zoomed = True
            logging.info("Minimap zoom completed; phase=town")
        elif phase == "combat":
            logging.info("Minimap zoom completed; phase=combat")

    def _minimap_zoom_position(self, window: WindowInfo, frame: np.ndarray, phase: str) -> tuple[int, int]:
        if phase == "town" and self.config.town_teleport.town_minimap_roi:
            left, top, width, height = self.config.town_teleport.town_minimap_roi
        else:
            route = self.config.walking.route
            left, top, width, height = minimap_bounds(
                frame.shape[1], frame.shape[0], route.minimap.right_px, route.minimap.top_px, route.minimap.width_px, route.minimap.height_px
            )
        return window.left + left + width // 2, window.top + top + height // 2

    def _run_minimap_zoom(self, window: WindowInfo, frame: np.ndarray, now: float) -> bool:
        minimap_zoom = getattr(self, "minimap_zoom", None)
        if minimap_zoom is None or not minimap_zoom.active:
            return False
        self._pause_for_login(window)
        action = minimap_zoom.next_action(now)
        if action:
            if action.phase == "combat" and action.remaining_steps == minimap_zoom.combat_scroll_steps - 1:
                logging.info("Minimap zoom started; phase=combat; direction=up; steps=%s", minimap_zoom.combat_scroll_steps)
            if not self.config.action.dry_run:
                ctrl_wheel_at(self._minimap_zoom_position(window, frame, action.phase), action.direction)
        if completed := minimap_zoom.consume_completion():
            self._handle_minimap_zoom_completion(completed, now)
        return action is not None or completed is not None or minimap_zoom.active

    def _start_town_minimap_zoom(self, town_teleport: TownTeleportController, frame: np.ndarray, now: float) -> bool:
        minimap_zoom = getattr(self, "minimap_zoom", None)
        if (
            minimap_zoom
            and minimap_zoom.enabled
            and not self._town_minimap_zoomed
            and not minimap_zoom.active
            and not town_teleport.active
            and town_teleport.is_town(frame)
        ):
            minimap_zoom.start_town(now)
            logging.info("Minimap zoom started; phase=town; direction=down; steps=%s", minimap_zoom.town_scroll_steps)
            return True
        return False

    def _scripted_route_step(self, window: WindowInfo, now: float) -> None:
        scripted_route = self.scripted_route
        if scripted_route is None:
            return
        keys = scripted_route.update(now)
        if not self.config.action.dry_run:
            self.movement_input.set_movement(window.hwnd, keys)
        if scripted_route.state != self.scripted_route_state:
            logging.info("Scripted route state=%s; segment=%s; keys=%s", scripted_route.state, scripted_route.segment_index, keys)
            self.scripted_route_state = scripted_route.state

    def _route_player_position(self, minimap: np.ndarray, marker_position: tuple[int, int] | None) -> tuple[int, int] | None:
        if marker_position is None:
            return None
        if self.localizer is None:
            return marker_position
        minimap_origin = self.localizer.locate(minimap)
        if minimap_origin is None:
            return None
        return minimap_origin[0] + marker_position[0], minimap_origin[1] + marker_position[1]

    def _detect_targets(self, frame: np.ndarray) -> tuple[DetectionResult, ...]:
        roi_left, roi_top, roi_width, roi_height = center_roi_bounds(frame.shape[1], frame.shape[0], self.config.detection.center_roi)
        task_frame = frame[roi_top:roi_top + roi_height, roi_left:roi_left + roi_width]
        if self.negative_detector and self.negative_detector.detect(task_frame):
            return ()
        if self.hsv_detector:
            hsv_targets = tuple(translate_detection(target, roi_left, roi_top) for target in self.hsv_detector.detect_all(task_frame))
            if hsv_targets:
                return hsv_targets
        if self.map_target_detector and (template_detection := self.map_target_detector.detect(task_frame)):
            return (translate_detection(template_detection, roi_left, roi_top),)
        if self.detector and (template_detection := self.detector.detect(task_frame)):
            return (translate_detection(template_detection, roi_left, roi_top),)
        return ()

    def run(self, once: bool = False) -> None:
        while True:
            detection_started_at = time.monotonic()
            window = find_window(self.config.target_window_title)
            self.current_hwnd = window.hwnd
            frame = self.capture(window)
            captured_at = time.monotonic()
            disconnect_recovery = getattr(self, "disconnect_recovery", None)
            if disconnect_recovery:
                disconnect_action = disconnect_recovery.handle(frame)
                if disconnect_recovery.active:
                    if disconnect_action:
                        self._handle_disconnect_action(window, disconnect_action)
                    else:
                        self._pause_for_login(window)
                    if once:
                        return
                    self._sleep_until_next_poll(detection_started_at)
                    continue
            death_recovery = getattr(self, "death_recovery", None)
            if death_recovery:
                death_action = death_recovery.handle(frame)
                if death_recovery.active:
                    if death_action:
                        self._handle_death_action(window, death_action)
                    else:
                        self._pause_for_login(window)
                    if once:
                        return
                    self._sleep_until_next_poll(detection_started_at)
                    continue
            login_recovery = getattr(self, "login_recovery", None)
            if login_recovery:
                login_action = login_recovery.handle(frame, captured_at)
                if login_recovery.active:
                    self._cancel_minimap_zoom()
                    self._cancel_route_playback()
                    if login_action:
                        self._handle_login_action(window, login_action)
                    else:
                        self._pause_for_login(window)
                    if once:
                        return
                    self._sleep_until_next_poll(detection_started_at)
                    continue
            town_teleport = getattr(self, "town_teleport", None)
            if town_teleport:
                self._start_town_minimap_zoom(town_teleport, frame, captured_at)
                if self._run_minimap_zoom(window, frame, captured_at):
                    if once:
                        return
                    self._sleep_until_next_poll(detection_started_at)
                    continue
                teleport_action = town_teleport.handle(frame, captured_at)
                if town_teleport.active:
                    if teleport_action:
                        self._handle_teleport_action(window, teleport_action)
                    else:
                        self._pause_for_login(window)
                    if once:
                        return
                    self._sleep_until_next_poll(detection_started_at)
                    continue
                if town_teleport.consume_departure():
                    self._handle_teleport_departure(captured_at)
                    if self._run_minimap_zoom(window, frame, captured_at):
                        if once:
                            return
                        self._sleep_until_next_poll(detection_started_at)
                        continue
                if self._run_map_arrival_wait(window, frame, captured_at):
                    if once:
                        return
                    self._sleep_until_next_poll(detection_started_at)
                    continue
            targets = self._detect_targets(frame)
            detected_at = time.monotonic()
            now = detected_at
            target = select_nearest_to_center(targets, frame.shape[1], frame.shape[0]) if targets else None
            self._handle_combat_start(frame, now)

            # Target coordinates belong to this captured frame.  Handle pointer
            # and target skills before walking/navigation makes them stale.
            if target:
                image_position = (window.left + target.left + target.width // 2, window.top + target.top + target.height // 2)
                cursor_position = image_hover_position(window, target, self.config.pointer.offset_y)
                self.was_detected = True
                self._handle_task_one(window, target, cursor_position, now)
                if self._is_center_hsv_target(window, target):
                    self._handle_center_target(now, image_position)
                if self.config.runtime.save_debug_frame:
                    self.annotate(frame, target)
                    debug_path = self.base_dir / self.config.runtime.debug_frame_path
                    debug_path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(debug_path), frame)
            else:
                self.was_detected = False
                self.was_task_action_logged = False
                self.was_center_detected = False

            if not self.config.action.dry_run:
                self.skill_input.process(window.hwnd, now)

            crowd_key = self.combat.observe(now, len(targets)) if self.combat else None
            scripted_route = getattr(self, "scripted_route", None)
            route_playback_active = bool(scripted_route and scripted_route.active)
            avoid_crowd = bool(
                getattr(self.config.crowd_combat, "avoid_movement_enabled", True)
                and self.combat
                and target
                and self.combat.should_avoid_crowd(len(targets))
                and not route_playback_active
            )
            if scripted_route and scripted_route.active:
                self._scripted_route_step(window, now)
            elif self.walker and now >= self.next_walk_at:
                excluded_keys = directions_toward_target(target, frame.shape[1], frame.shape[0]) if avoid_crowd else ()
                keys, distance = self.walker.next_step(excluded_keys=excluded_keys)
                if not self.config.action.dry_run:
                    self.movement_input.set_movement(window.hwnd, keys)
                    if avoid_crowd:
                        logging.info("Crowd avoidance; targets=%s; blocked=%s; movement=%s", len(targets), excluded_keys, keys)
                self.next_walk_at = now + distance / self.config.walking.speed_px_per_sec
            elif self.navigator:
                route = self.config.walking.route
                map_left, map_top, map_width, map_height = minimap_bounds(
                    frame.shape[1],
                    frame.shape[0],
                    route.minimap.right_px,
                    route.minimap.top_px,
                    route.minimap.width_px,
                    route.minimap.height_px,
                )
                minimap = frame[map_top:map_top + map_height, map_left:map_left + map_width]
                marker_position = find_white_pair(minimap, route.white_threshold, route.pair_max_distance_px)
                player_position = self._route_player_position(minimap, marker_position)
                if player_position:
                    route_target = self.navigator.update_target(player_position)
                    if route_target.name != self.route_target_name:
                        logging.info("Route target=%s; player=%s; map target=(%s, %s)", route_target.name, player_position, route_target.x, route_target.y)
                        self.route_target_name = route_target.name
                    if not self.config.action.dry_run:
                        keys = self.navigator.movement_keys(player_position)
                        if avoid_crowd:
                            keys = steer_away_from_target(keys, target, frame.shape[1], frame.shape[0])
                        self.movement_input.set_movement(window.hwnd, keys)
                        if avoid_crowd:
                            logging.info("Crowd avoidance; targets=%s; movement=%s", len(targets), keys)
                elif not self.config.action.dry_run:
                    self.movement_input.set_movement(window.hwnd, ())
            if crowd_key and not self.config.action.dry_run:
                self.skill_input.queue_tap(crowd_key)
                logging.info("Crowd skill action; targets=%s; key=%s", len(targets), crowd_key)
            if self.scheduler:
                self.scheduler.tick(now)
                if key := self.scheduler.pop_ready(now):
                    if not self.config.action.dry_run:
                        self.skill_input.queue_tap(key)

            if not self.config.action.dry_run:
                self.skill_input.process(window.hwnd, now)
            if monitor := getattr(self, "timing_monitor", None):
                if report := monitor.record(
                    detection_started_at,
                    capture_ms=(captured_at - detection_started_at) * 1000,
                    detection_ms=(detected_at - captured_at) * 1000,
                    action_ms=(time.monotonic() - detected_at) * 1000,
                ):
                    logging.debug(
                        "Detection timing; target=%sms; samples=%s; mean=%.1fms; max=%.1fms; over_target=%s; capture=%.1fms; detect=%.1fms; action=%.1fms",
                        monitor.target_interval_ms,
                        report.sample_count,
                        report.mean_interval_ms,
                        report.max_interval_ms,
                        report.over_target_count,
                        report.mean_capture_ms,
                        report.mean_detection_ms,
                        report.mean_action_ms,
                    )
            if once:
                return
            self._sleep_until_next_poll(detection_started_at)
