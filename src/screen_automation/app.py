from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import mss
import numpy as np
import win32api

from .center_target import is_inside_window_center_radius
from .combat import CombatController, CrowdSkillGroup, directions_toward_target, select_nearest_to_center, steer_away_from_target
from .config import AppConfig
from .detector import DetectionResult, MultiTemplateDetector
from .hsv_bar import HSVBarDetector
from .input_coordinator import MovementInput, SkillTapQueue
from .login_recovery import LoginAction, LoginRecoveryController
from .map_localization import MapLocalizer
from .navigation import RouteNavigator, Waypoint, find_white_pair, minimap_bounds
from .pointer import click_screen_position, image_hover_position, move_cursor_to_image
from .roi import center_roi_bounds, translate_detection
from .skill_queue import SkillScheduler
from .timing import DetectionTimingMonitor
from .walking import WalkingController
from .window import WindowInfo, capture_print_window, find_window


class AutomationApp:
    def __init__(self, config: AppConfig, base_dir: Path) -> None:
        self.config = config
        self.base_dir = base_dir
        self.detector = (
            MultiTemplateDetector(tuple(base_dir / path for path in config.detection.template_paths), config.detection.threshold, config.detection.roi)
            if config.detection.template_paths else None
        )
        self.negative_detector = (
            MultiTemplateDetector(tuple(base_dir / path for path in config.detection.negative_template_paths), config.detection.threshold, config.detection.roi)
            if config.detection.negative_template_paths else None
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
        self.walker = WalkingController(config.walking.step_distance, config.walking.boundary_x, config.walking.boundary_y) if config.walking.enabled and config.walking.mode == "random" else None
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
        self.next_walk_at = 0.0
        self.combat = (
            CombatController(
                CrowdSkillGroup(
                    config.crowd_combat.keys,
                    config.crowd_combat.min_targets,
                    config.crowd_combat.skill_cooldown_ms / 1000,
                    config.crowd_combat.skill_interval_ms / 1000,
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

    def stop(self) -> None:
        if self.current_hwnd and not self.config.action.dry_run:
            self.movement_input.release(self.current_hwnd)
        self.skill_input.clear()

    def capture(self, window: WindowInfo) -> np.ndarray:
        try:
            if self.config.capture.method == "printwindow":
                return capture_print_window(window)
        except RuntimeError as error:
            if not self.config.capture.fallback_to_desktop:
                raise
            logging.warning("PrintWindow capture failed; using desktop capture: %s", error)
        with mss.mss() as sct:
            shot = sct.grab({"left": window.left, "top": window.top, "width": window.width, "height": window.height})
            return np.asarray(shot)[:, :, :3].copy()

    def annotate(self, frame: np.ndarray, detection: DetectionResult) -> None:
        cv2.rectangle(frame, (detection.left, detection.top), (detection.left + detection.width, detection.top + detection.height), (0, 255, 0), 2)
        cv2.putText(frame, f"score={detection.score:.3f}", (detection.left, max(18, detection.top - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    def _is_center_hsv_target(self, window: WindowInfo, detection: DetectionResult) -> bool:
        return self.config.center_target.enabled and is_inside_window_center_radius(window, detection, self.config.center_target.radius_px)

    def _handle_center_target(self, now: float, image_position: tuple[int, int]) -> None:
        if now - self.last_center_action_at >= self.config.center_target.repeat_interval_ms / 1000:
            if not self.config.action.dry_run:
                self.skill_input.queue_tap(self.config.center_target.key, coalesce=True)
                logging.info("Center skill action; screen position=%s; key=%s", image_position, self.config.center_target.key)
            self.last_center_action_at = now
        self.was_center_detected = True
        self.was_task_action_logged = False

    def _handle_task_one(self, window: WindowInfo, detection: DetectionResult, cursor_position: tuple[int, int], now: float) -> None:
        self.was_center_detected = False
        if now - self.last_action_at < self.config.action.repeat_interval_ms / 1000:
            return
        if not self.config.action.dry_run:
            move_cursor_to_image(window, detection, self.config.pointer.offset_y)
            self.skill_input.queue_tap(self.config.action.key, coalesce=True)
            if not self.was_task_action_logged:
                logging.info("Task 1 action; cursor target=%s; cursor=%s; key=%s", cursor_position, win32api.GetCursorPos(), self.config.action.key)
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
        if self.detector and (template_detection := self.detector.detect(task_frame)):
            return (translate_detection(template_detection, roi_left, roi_top),)
        if self.hsv_detector:
            return tuple(translate_detection(target, roi_left, roi_top) for target in self.hsv_detector.detect_all(task_frame))
        return ()

    def run(self, once: bool = False) -> None:
        while True:
            detection_started_at = time.monotonic()
            window = find_window(self.config.target_window_title)
            self.current_hwnd = window.hwnd
            frame = self.capture(window)
            captured_at = time.monotonic()
            login_recovery = getattr(self, "login_recovery", None)
            if login_recovery:
                login_action = login_recovery.handle(frame, captured_at)
                if login_recovery.active:
                    if login_action:
                        self._handle_login_action(window, login_action)
                    else:
                        self._pause_for_login(window)
                    if once:
                        return
                    time.sleep(self.config.runtime.poll_interval_ms / 1000)
                    continue
            targets = self._detect_targets(frame)
            detected_at = time.monotonic()
            now = detected_at
            target = select_nearest_to_center(targets, frame.shape[1], frame.shape[0]) if targets else None
            crowd_key = self.combat.observe(now, len(targets)) if self.combat else None
            avoid_crowd = bool(self.combat and target and self.combat.should_avoid_crowd(len(targets)))
            if self.walker and now >= self.next_walk_at:
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

            if target:
                image_position = (window.left + target.left + target.width // 2, window.top + target.top + target.height // 2)
                cursor_position = image_hover_position(window, target, self.config.pointer.offset_y)
                self.was_detected = True
                self.annotate(frame, target)
                if self.config.runtime.save_debug_frame:
                    debug_path = self.base_dir / self.config.runtime.debug_frame_path
                    debug_path.parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(debug_path), frame)
                self._handle_task_one(window, target, cursor_position, now)
                if self._is_center_hsv_target(window, target):
                    self._handle_center_target(now, image_position)
            else:
                self.was_detected = False
                self.was_task_action_logged = False
                self.was_center_detected = False

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
            time.sleep(self.config.runtime.poll_interval_ms / 1000)
