from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

import yaml


def _parse_skill_configs(
    raw_skills: object,
    fallback_skills: tuple[tuple[str, int], ...],
    setting_name: str,
) -> tuple["SkillConfig", ...]:
    if raw_skills is None:
        return tuple(SkillConfig(key, cooldown_ms) for key, cooldown_ms in fallback_skills)
    if not isinstance(raw_skills, list) or not raw_skills:
        raise ValueError(f"{setting_name}.skills must be a non-empty list")
    try:
        skills = tuple(
            SkillConfig(key=str(item["key"]), cooldown_ms=int(item["cooldown_ms"]))
            for item in raw_skills
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{setting_name}.skills entries require key and cooldown_ms") from error
    if any(not skill.key or skill.cooldown_ms <= 0 for skill in skills) or len({skill.key for skill in skills}) != len(skills):
        raise ValueError(f"{setting_name}.skills must use unique non-empty keys and positive cooldown_ms")
    return skills


@dataclass(frozen=True)
class CaptureConfig:
    method: str
    fallback_to_desktop: bool


@dataclass(frozen=True)
class CenterROIConfig:
    enabled: bool
    width: int
    height: int
    offset_y: int


@dataclass(frozen=True)
class DetectionConfig:
    template_paths: tuple[str, ...]
    negative_template_paths: tuple[str, ...]
    threshold: float
    roi: tuple[int, int, int, int] | None
    center_roi: CenterROIConfig


@dataclass(frozen=True)
class SkillConfig:
    key: str
    cooldown_ms: int


@dataclass(frozen=True)
class ActionConfig:
    key: str
    dry_run: bool
    key_hold_ms: int
    repeat_interval_ms: int
    skill_interval_ms: int
    skills: tuple[SkillConfig, ...]


@dataclass(frozen=True)
class PointerConfig:
    offset_y: int


@dataclass(frozen=True)
class CenterTargetConfig:
    enabled: bool
    template_paths: tuple[str, ...]
    radius_px: int
    key: str
    key_hold_ms: int
    repeat_interval_ms: int
    skill_interval_ms: int
    skills: tuple[SkillConfig, ...]


@dataclass(frozen=True)
class CrowdCombatConfig:
    enabled: bool
    avoid_movement_enabled: bool
    keys: tuple[str, ...]
    min_targets: int
    skill_cooldown_ms: int
    skill_interval_ms: int
    skills: tuple[SkillConfig, ...]

@dataclass(frozen=True)
class RouteMinimapConfig:
    right_px: int
    top_px: int
    width_px: int
    height_px: int


@dataclass(frozen=True)
class RouteWaypointConfig:
    name: str
    x: int
    y: int


@dataclass(frozen=True)
class RouteMapRecordingConfig:
    enabled: bool
    manifest_path: str
    min_match_count: int
    max_position_jump_px: int


@dataclass(frozen=True)
class RouteConfig:
    minimap: RouteMinimapConfig
    white_threshold: int
    pair_max_distance_px: int
    arrival_radius_px: int
    movement_deadzone_px: int
    map_recording: RouteMapRecordingConfig
    waypoints: tuple[RouteWaypointConfig, ...]


@dataclass(frozen=True)
class WalkingConfig:
    enabled: bool
    mode: str
    step_distance: float
    speed_px_per_sec: float
    boundary_x: float
    boundary_y: float
    route: RouteConfig

@dataclass(frozen=True)
class SkillQueueConfig:
    enabled: bool; queue_interval_ms: int; schedules: tuple[tuple[str, float], ...]

@dataclass(frozen=True)
class HSVBlackResidualConfig:
    min_extent: float = 0.75
    dedup_iou: float = 0.30
    outer_ring_px: int = 3
    min_outer_contrast: float = 8.0
    low_colour_trigger_ratio: float = 0.15


@dataclass(frozen=True)
class HSVBarConfig:
    enabled: bool
    min_width: int
    max_height: int
    min_aspect_ratio: float
    max_width: int = 160
    min_height: int = 12
    max_aspect_ratio: float = 12.0
    max_white_ratio: float = 0.80
    min_horizontal_run_ratio: float = 0.65
    min_allowed_colour_ratio: float = 0.60
    edge_band_px: int = 2
    edge_black_ratio: float = 0.50
    inner_band_enabled: bool = True
    black_residual_enabled: bool = False
    black_residual: HSVBlackResidualConfig = field(default_factory=HSVBlackResidualConfig)


@dataclass(frozen=True)
class RuntimeConfig:
    poll_interval_ms: int
    detection_timing_log_interval_ms: int
    log_mode: str
    save_debug_frame: bool
    debug_frame_path: str


@dataclass(frozen=True)
class LoginServerConfig:
    name: str
    template_path: str
    connect_template_path: str


@dataclass(frozen=True)
class LoginCharacterConfig:
    name: str
    template_path: str
    play_template_path: str


@dataclass(frozen=True)
class LoginRecoveryConfig:
    enabled: bool
    threshold: float
    action_delay_ms: int
    server: LoginServerConfig
    character: LoginCharacterConfig


@dataclass(frozen=True)
class DisconnectRecoveryConfig:
    enabled: bool
    threshold: float
    confirm_template_path: str


@dataclass(frozen=True)
class TownTeleportDestinationConfig:
    name: str
    template_path: str


@dataclass(frozen=True)
class TownTeleportConfig:
    enabled: bool
    threshold: float
    action_delay_ms: int
    stage_timeout_ms: int
    town_minimap_template_path: str
    town_minimap_roi: tuple[int, int, int, int] | None
    consumables_template_path: str
    waystone_template_path: str
    waystone_confirm_template_path: str
    waystone_confirm_template_paths: tuple[str, ...]
    teleport_confirm_template_path: str
    destination: TownTeleportDestinationConfig


@dataclass(frozen=True)
class MapProfileConfig:
    """Assets and route data that change together when the combat map changes."""

    name: str
    teleport_template_path: str
    target_template_paths: tuple[str, ...]
    movement_script_path: str | None
    arrival_minimap_template_path: str | None
    arrival_minimap_threshold: float
    route_start_delay_ms: int


@dataclass(frozen=True)
class MinimapZoomConfig:
    enabled: bool
    town_scroll_steps: int
    combat_scroll_steps: int
    interval_ms: int
    combat_load_wait_ms: int


@dataclass(frozen=True)
class CombatStartConfig:
    enabled: bool
    skills: tuple[str, ...]
    skill_interval_ms: int
    verify_delay_ms: int
    status_template_path: str
    status_threshold: float
    status_roi: tuple[int, int, int, int] | None


@dataclass(frozen=True)
class DeathRecoveryConfig:
    enabled: bool
    threshold: float
    town_respawn_template_path: str
    healer_enabled: bool
    healer_template_path: str
    healer_dialog_template_path: str
    healer_threshold: float


@dataclass(frozen=True)
class AppConfig:
    target_window_title: str
    capture: CaptureConfig
    detection: DetectionConfig
    action: ActionConfig
    pointer: PointerConfig
    center_target: CenterTargetConfig
    crowd_combat: CrowdCombatConfig
    walking: WalkingConfig
    skill_queue: SkillQueueConfig
    hsv_bar: HSVBarConfig
    runtime: RuntimeConfig
    login_recovery: LoginRecoveryConfig
    disconnect_recovery: DisconnectRecoveryConfig
    town_teleport: TownTeleportConfig
    active_map: MapProfileConfig
    minimap_zoom: MinimapZoomConfig
    combat_start: CombatStartConfig
    death_recovery: DeathRecoveryConfig


def load_config(path: Path) -> AppConfig:
    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    try:
        detection = raw["detection"]
        action = raw["action"]
        runtime = raw["runtime"]
        raw_log_mode = runtime.get("log_mode", "events")
        log_mode = "off" if raw_log_mode is False else str(raw_log_mode)
        if log_mode == "none":
            log_mode = "off"
        if log_mode not in {"off", "events", "diagnostic"}:
            raise ValueError("runtime.log_mode must be off, events, or diagnostic")
        roi = detection.get("roi")
        if roi is not None and (len(roi) != 4 or any(not isinstance(v, int) for v in roi)):
            raise ValueError("detection.roi 必須為 [left, top, width, height] 或 null")
        threshold = float(detection["threshold"])
        if not 0 <= threshold <= 1:
            raise ValueError("detection.threshold 必須介於 0 與 1")
        template_paths = tuple(str(value) for value in detection["template_paths"])
        negative_template_paths = tuple(str(value) for value in detection.get("negative_template_paths", []))
        center_roi = CenterROIConfig(**detection.get("center_roi", {"enabled": False, "width": 700, "height": 500, "offset_y": 0}))
        if center_roi.width <= 0 or center_roi.height <= 0:
            raise ValueError("detection.center_roi.width 與 height 必須大於 0")
        walking_raw = raw.get("walking", {})
        route_raw = walking_raw.get("route", {})
        minimap = RouteMinimapConfig(**route_raw.get("minimap", {"right_px": 20, "top_px": 20, "width_px": 330, "height_px": 330}))
        map_recording = RouteMapRecordingConfig(
            enabled=bool(route_raw.get("map_recording", {}).get("enabled", False)),
            manifest_path=str(route_raw.get("map_recording", {}).get("manifest_path", "")),
            min_match_count=int(route_raw.get("map_recording", {}).get("min_match_count", 8)),
            max_position_jump_px=int(route_raw.get("map_recording", {}).get("max_position_jump_px", 80)),
        )
        if map_recording.min_match_count < 6 or map_recording.max_position_jump_px <= 0:
            raise ValueError("walking.route.map_recording settings are invalid")
        if "recorded_route" in walking_raw:
            raise ValueError("walking.recorded_route has been removed; use scripted_route instead")
        route = RouteConfig(
            minimap=minimap,
            white_threshold=int(route_raw.get("white_threshold", 220)),
            pair_max_distance_px=int(route_raw.get("pair_max_distance_px", 18)),
            arrival_radius_px=int(route_raw.get("arrival_radius_px", 12)),
            movement_deadzone_px=int(route_raw.get("movement_deadzone_px", 4)),
            map_recording=map_recording,
            waypoints=tuple(RouteWaypointConfig(str(point["name"]), int(point["x"]), int(point["y"])) for point in route_raw.get("waypoints", [])),
        )
        walking_mode = str(walking_raw.get("mode", "random"))
        if walking_mode not in {"random", "route", "scripted_route"}:
            raise ValueError("walking.mode must be random, route, or scripted_route")
        walking = WalkingConfig(
            enabled=bool(walking_raw.get("enabled", False)),
            mode=walking_mode,
            step_distance=float(walking_raw.get("step_distance", 0)),
            speed_px_per_sec=float(walking_raw.get("speed_px_per_sec", 1)),
            boundary_x=float(walking_raw.get("boundary_x", 0)),
            boundary_y=float(walking_raw.get("boundary_y", 0)),
            route=route,
        )
        crowd_raw = raw.get("crowd_combat", {})
        crowd_keys = tuple(str(key) for key in crowd_raw.get("keys", ["F2", "F3", "F4"]))
        crowd_cooldown_ms = int(crowd_raw.get("skill_cooldown_ms", 6000))
        crowd_interval_ms = int(crowd_raw.get("skill_interval_ms", 330))
        crowd_skills = _parse_skill_configs(
            crowd_raw.get("skills"),
            tuple((key, crowd_cooldown_ms) for key in crowd_keys),
            "crowd_combat",
        )
        crowd_combat = CrowdCombatConfig(
            enabled=bool(crowd_raw.get("enabled", False)),
            avoid_movement_enabled=bool(crowd_raw.get("avoid_movement_enabled", True)),
            keys=crowd_keys,
            min_targets=int(crowd_raw.get("min_targets", 3)),
            skill_cooldown_ms=crowd_cooldown_ms,
            skill_interval_ms=crowd_interval_ms,
            skills=crowd_skills,
        )
        if not crowd_combat.keys or crowd_combat.min_targets < 1 or min(
            crowd_combat.skill_cooldown_ms, crowd_combat.skill_interval_ms
        ) <= 0:
            raise ValueError("crowd_combat settings are invalid")
        action_interval_ms = int(action.get("skill_interval_ms", action["repeat_interval_ms"]))
        action_skills = _parse_skill_configs(
            action.get("skills"),
            ((str(action["key"]), int(action["repeat_interval_ms"])),),
            "action",
        )
        center_raw = raw["center_target"]
        center_interval_ms = int(center_raw.get("skill_interval_ms", center_raw["repeat_interval_ms"]))
        center_skills = _parse_skill_configs(
            center_raw.get("skills"),
            ((str(center_raw["key"]), int(center_raw["repeat_interval_ms"])),),
            "center_target",
        )
        if action_interval_ms <= 0 or center_interval_ms <= 0:
            raise ValueError("action and center_target skill_interval_ms must be positive")
        hsv_bar_raw = dict(raw.get("hsv_bar", {"enabled": False, "min_width": 60, "max_height": 35, "min_aspect_ratio": 4.0}))
        black_residual = HSVBlackResidualConfig(**hsv_bar_raw.pop("black_residual", {}))
        hsv_bar = HSVBarConfig(**hsv_bar_raw, black_residual=black_residual)
        if hsv_bar.edge_band_px <= 0 or not 0 < hsv_bar.edge_black_ratio <= 1:
            raise ValueError("hsv_bar edge settings are invalid")
        if (
            not 0 < black_residual.min_extent <= 1
            or not 0 < black_residual.dedup_iou <= 1
            or black_residual.outer_ring_px <= 0
            or black_residual.min_outer_contrast < 0
            or not 0 <= black_residual.low_colour_trigger_ratio <= 1
        ):
            raise ValueError("hsv_bar.black_residual settings are invalid")
        login_raw = raw.get("login_recovery", {})
        login_threshold = float(login_raw.get("threshold", 0.82))
        login_delay_ms = int(login_raw.get("action_delay_ms", 700))
        if not 0 <= login_threshold <= 1 or login_delay_ms < 0:
            raise ValueError("login_recovery settings are invalid")
        login_recovery = LoginRecoveryConfig(
            enabled=bool(login_raw.get("enabled", False)),
            threshold=login_threshold,
            action_delay_ms=login_delay_ms,
            server=LoginServerConfig(
                name=str(login_raw.get("server", {}).get("name", "SEA")),
                template_path=str(login_raw.get("server", {}).get("template_path", "assets/login/server/sea.png")),
                connect_template_path=str(login_raw.get("server", {}).get("connect_template_path", "assets/login/server/connect.png")),
            ),
            character=LoginCharacterConfig(
                name=str(login_raw.get("character", {}).get("name", "滴滴殺手")),
                template_path=str(login_raw.get("character", {}).get("template_path", "assets/login/character/didi_killer.png")),
                play_template_path=str(login_raw.get("character", {}).get("play_template_path", "assets/login/character/play.png")),
            ),
        )
        disconnect_raw = raw.get("disconnect_recovery", {})
        disconnect_threshold = float(disconnect_raw.get("threshold", 0.82))
        if not 0 <= disconnect_threshold <= 1:
            raise ValueError("disconnect_recovery threshold must be between 0 and 1")
        disconnect_recovery = DisconnectRecoveryConfig(
            enabled=bool(disconnect_raw.get("enabled", False)),
            threshold=disconnect_threshold,
            confirm_template_path=str(disconnect_raw.get("confirm_template_path", "assets/disconnect/confirm.png")),
        )
        if not disconnect_recovery.confirm_template_path:
            raise ValueError("disconnect_recovery confirm_template_path must not be empty")
        teleport_raw = raw.get("town_teleport", {})
        teleport_threshold = float(teleport_raw.get("threshold", 0.82))
        teleport_delay_ms = int(teleport_raw.get("action_delay_ms", 700))
        teleport_timeout_ms = int(teleport_raw.get("stage_timeout_ms", 8000))
        if not 0 <= teleport_threshold <= 1 or teleport_delay_ms < 0 or teleport_timeout_ms <= 0:
            raise ValueError("town_teleport settings are invalid")
        teleport_destination = teleport_raw.get("destination", {})
        teleport_roi_raw = teleport_raw.get("town_minimap_roi")
        if teleport_roi_raw is not None and (len(teleport_roi_raw) != 4 or any(not isinstance(value, int) for value in teleport_roi_raw)):
            raise ValueError("town_teleport.town_minimap_roi must be [left, top, width, height] or null")
        town_teleport = TownTeleportConfig(
            enabled=bool(teleport_raw.get("enabled", False)),
            threshold=teleport_threshold,
            action_delay_ms=teleport_delay_ms,
            stage_timeout_ms=teleport_timeout_ms,
            town_minimap_template_path=str(teleport_raw.get("town_minimap_template_path", "assets/teleport/city_minimap.png")),
            town_minimap_roi=tuple(teleport_roi_raw) if teleport_roi_raw else None,
            consumables_template_path=str(teleport_raw.get("consumables_template_path", "assets/teleport/consumables.png")),
            waystone_template_path=str(teleport_raw.get("waystone_template_path", "assets/teleport/waystone.png")),
            waystone_confirm_template_path=str(teleport_raw.get("waystone_confirm_template_path", "assets/teleport/waystone_confirm.png")),
            waystone_confirm_template_paths=tuple(
                str(value)
                for value in teleport_raw.get(
                    "waystone_confirm_template_paths",
                    [teleport_raw.get("waystone_confirm_template_path", "assets/teleport/waystone_confirm.png")],
                )
            ),
            teleport_confirm_template_path=str(teleport_raw.get("teleport_confirm_template_path", "assets/teleport/teleport_confirm.png")),
            destination=TownTeleportDestinationConfig(
                name=str(teleport_destination.get("name", "demon_mouth")),
                template_path=str(teleport_destination.get("template_path", "assets/teleport/maps/demon_mouth.png")),
            ),
        )
        maps_raw = raw.get("maps")
        active_map_name = raw.get("active_map")
        if maps_raw is None and active_map_name is None:
            active_map = MapProfileConfig(
                name=town_teleport.destination.name,
                teleport_template_path=town_teleport.destination.template_path,
                target_template_paths=(),
                movement_script_path=None,
                arrival_minimap_template_path=None,
                arrival_minimap_threshold=0.85,
                route_start_delay_ms=0,
            )
        else:
            if not isinstance(maps_raw, dict) or not isinstance(active_map_name, str) or active_map_name not in maps_raw:
                raise ValueError("active_map must name an entry in maps")
            active_map_raw = maps_raw[active_map_name]
            if not isinstance(active_map_raw, dict):
                raise ValueError("maps entries must be mappings")
            default_map_dir = f"assets/maps/{active_map_name}"
            teleport_template_path = active_map_raw.get(
                "teleport_template_path", f"{default_map_dir}/teleport.png"
            )
            target_template_paths = active_map_raw.get(
                "target_template_paths", [f"{default_map_dir}/targets"]
            )
            movement_script_path = active_map_raw.get(
                "movement_script_path", f"{default_map_dir}/movement.yaml"
            )
            arrival_minimap_template_path = active_map_raw.get(
                "arrival_minimap_template_path", f"{default_map_dir}/arrival_minimap.png"
            )
            arrival_minimap_threshold = float(active_map_raw.get("arrival_minimap_threshold", detection["threshold"]))
            route_start_delay_ms = int(active_map_raw.get("route_start_delay_ms", 0))
            if not isinstance(teleport_template_path, str) or not teleport_template_path:
                raise ValueError("maps.<name>.teleport_template_path must be a non-empty string")
            if not isinstance(target_template_paths, list) or any(not isinstance(item, str) or not item for item in target_template_paths):
                raise ValueError("maps.<name>.target_template_paths must be a list of non-empty strings")
            if movement_script_path is not None and (not isinstance(movement_script_path, str) or not movement_script_path):
                raise ValueError("maps.<name>.movement_script_path must be a string or null")
            if arrival_minimap_template_path is not None and (not isinstance(arrival_minimap_template_path, str) or not arrival_minimap_template_path):
                raise ValueError("maps.<name>.arrival_minimap_template_path must be a string or null")
            if not 0 <= arrival_minimap_threshold <= 1:
                raise ValueError("maps.<name>.arrival_minimap_threshold must be between 0 and 1")
            if route_start_delay_ms < 0:
                raise ValueError("maps.<name>.route_start_delay_ms must be non-negative")
            active_map = MapProfileConfig(
                name=active_map_name,
                teleport_template_path=teleport_template_path,
                target_template_paths=tuple(target_template_paths),
                movement_script_path=movement_script_path,
                arrival_minimap_template_path=arrival_minimap_template_path,
                arrival_minimap_threshold=arrival_minimap_threshold,
                route_start_delay_ms=route_start_delay_ms,
            )
            town_teleport = replace(
                town_teleport,
                destination=TownTeleportDestinationConfig(active_map.name, active_map.teleport_template_path),
            )
        if walking.mode == "scripted_route" and active_map.movement_script_path is None:
            raise ValueError("active_map requires movement_script_path when walking.mode is scripted_route")
        minimap_zoom_raw = raw.get("minimap_zoom", {})
        minimap_zoom = MinimapZoomConfig(
            enabled=bool(minimap_zoom_raw.get("enabled", False)),
            town_scroll_steps=int(minimap_zoom_raw.get("town_scroll_steps", 30)),
            combat_scroll_steps=int(minimap_zoom_raw.get("combat_scroll_steps", 30)),
            interval_ms=int(minimap_zoom_raw.get("interval_ms", 10)),
            combat_load_wait_ms=int(minimap_zoom_raw.get("combat_load_wait_ms", 5000)),
        )
        if min(
            minimap_zoom.town_scroll_steps,
            minimap_zoom.combat_scroll_steps,
            minimap_zoom.interval_ms,
            minimap_zoom.combat_load_wait_ms,
        ) < 0 or minimap_zoom.interval_ms == 0:
            raise ValueError("minimap_zoom settings are invalid")
        if "combat_state" in raw:
            raise ValueError("combat_state has been removed; use combat_start instead")
        combat_start_raw = raw.get("combat_start", {})
        raw_combat_start_skills = combat_start_raw.get("skills", [])
        if not isinstance(raw_combat_start_skills, list):
            raise ValueError("combat_start.skills must be a list")
        try:
            combat_start_skills = tuple(str(skill["key"]) for skill in raw_combat_start_skills)
        except (KeyError, TypeError):
            raise ValueError("combat_start.skills entries must contain key") from None
        combat_start = CombatStartConfig(
            enabled=bool(combat_start_raw.get("enabled", False)),
            skills=combat_start_skills,
            skill_interval_ms=int(combat_start_raw.get("skill_interval_ms", 330)),
            verify_delay_ms=int(combat_start_raw.get("verify_delay_ms", 500)),
            status_template_path=str(combat_start_raw.get("status_template_path", "assets/combat/combat_state_icon.png")),
            status_threshold=float(combat_start_raw.get("status_threshold", 0.85)),
            status_roi=tuple(combat_start_raw["status_roi"]) if combat_start_raw.get("status_roi") else None,
        )
        if (
            combat_start.skill_interval_ms < 0
            or combat_start.verify_delay_ms <= 0
            or not 0 <= combat_start.status_threshold <= 1
            or any(not key for key in combat_start.skills)
            or not combat_start.status_template_path
            or (
                combat_start.status_roi is not None
                and (len(combat_start.status_roi) != 4 or any(not isinstance(value, int) for value in combat_start.status_roi))
            )
        ):
            raise ValueError("combat_start settings are invalid")
        death_raw = raw.get("death_recovery", {})
        death_threshold = float(death_raw.get("threshold", 0.82))
        if not 0 <= death_threshold <= 1:
            raise ValueError("death_recovery threshold must be between 0 and 1")
        death_recovery = DeathRecoveryConfig(
            enabled=bool(death_raw.get("enabled", False)),
            threshold=death_threshold,
            town_respawn_template_path=str(death_raw.get("town_respawn_template_path", "assets/death/town_respawn.png")),
            healer_enabled=bool(death_raw.get("healer_enabled", False)),
            healer_template_path=str(death_raw.get("healer_template_path", "assets/death/healer.png")),
            healer_dialog_template_path=str(death_raw.get("healer_dialog_template_path", "assets/death/healer_dialog.png")),
            healer_threshold=float(death_raw.get("healer_threshold", death_threshold)),
        )
        if not 0 <= death_recovery.healer_threshold <= 1:
            raise ValueError("death_recovery healer_threshold must be between 0 and 1")
        return AppConfig(
            target_window_title=str(raw["target_window_title"]),
            capture=CaptureConfig(**raw["capture"]),
            detection=DetectionConfig(template_paths, negative_template_paths, threshold, tuple(roi) if roi else None, center_roi),
            action=ActionConfig(
                key=str(action["key"]),
                dry_run=bool(action["dry_run"]),
                key_hold_ms=int(action["key_hold_ms"]),
                repeat_interval_ms=int(action["repeat_interval_ms"]),
                skill_interval_ms=action_interval_ms,
                skills=action_skills,
            ),
            pointer=PointerConfig(offset_y=int(raw["pointer"]["offset_y"])),
            center_target=CenterTargetConfig(
                enabled=bool(center_raw.get("enabled", True)),
                template_paths=tuple(str(value) for value in center_raw["template_paths"]),
                radius_px=int(center_raw["radius_px"]),
                key=str(center_raw["key"]),
                key_hold_ms=int(center_raw["key_hold_ms"]),
                repeat_interval_ms=int(center_raw["repeat_interval_ms"]),
                skill_interval_ms=center_interval_ms,
                skills=center_skills,
            ),
            crowd_combat=crowd_combat,
            walking=walking,
            skill_queue=SkillQueueConfig(bool(raw.get("skill_queue", {}).get("enabled", False)), int(raw.get("skill_queue", {}).get("queue_interval_ms", 330)), tuple((str(item["key"]), float(item["interval_seconds"])) for item in raw.get("skill_queue", {}).get("schedules", []))),
            hsv_bar=hsv_bar,
            runtime=RuntimeConfig(
                poll_interval_ms=int(runtime["poll_interval_ms"]),
                detection_timing_log_interval_ms=int(runtime.get("detection_timing_log_interval_ms", 5000)),
                log_mode=log_mode,
                save_debug_frame=bool(runtime["save_debug_frame"]),
                debug_frame_path=str(runtime["debug_frame_path"]),
            ),
            login_recovery=login_recovery,
            disconnect_recovery=disconnect_recovery,
            town_teleport=town_teleport,
            active_map=active_map,
            minimap_zoom=minimap_zoom,
            combat_start=combat_start,
            death_recovery=death_recovery,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"設定檔格式錯誤：{error}") from error
