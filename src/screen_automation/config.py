from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


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
class ActionConfig:
    key: str
    dry_run: bool
    key_hold_ms: int
    repeat_interval_ms: int


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


@dataclass(frozen=True)
class CrowdCombatConfig:
    enabled: bool
    keys: tuple[str, ...]
    min_targets: int
    skill_cooldown_ms: int
    skill_interval_ms: int

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
    teleport_confirm_template_path: str
    destination: TownTeleportDestinationConfig


@dataclass(frozen=True)
class DeathRecoveryConfig:
    enabled: bool
    threshold: float
    town_respawn_template_path: str


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
    town_teleport: TownTeleportConfig
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
        if walking_mode not in {"random", "route"}:
            raise ValueError("walking.mode 必須是 random 或 route")
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
        crowd_combat = CrowdCombatConfig(
            enabled=bool(crowd_raw.get("enabled", False)),
            keys=tuple(str(key) for key in crowd_raw.get("keys", ["F2", "F3", "F4"])),
            min_targets=int(crowd_raw.get("min_targets", 3)),
            skill_cooldown_ms=int(crowd_raw.get("skill_cooldown_ms", 6000)),
            skill_interval_ms=int(crowd_raw.get("skill_interval_ms", 330)),
        )
        if not crowd_combat.keys or crowd_combat.min_targets < 1 or min(
            crowd_combat.skill_cooldown_ms, crowd_combat.skill_interval_ms
        ) < 0:
            raise ValueError("crowd_combat settings are invalid")
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
            teleport_confirm_template_path=str(teleport_raw.get("teleport_confirm_template_path", "assets/teleport/teleport_confirm.png")),
            destination=TownTeleportDestinationConfig(
                name=str(teleport_destination.get("name", "demon_mouth")),
                template_path=str(teleport_destination.get("template_path", "assets/teleport/maps/demon_mouth.png")),
            ),
        )
        death_raw = raw.get("death_recovery", {})
        death_threshold = float(death_raw.get("threshold", 0.82))
        if not 0 <= death_threshold <= 1:
            raise ValueError("death_recovery threshold must be between 0 and 1")
        death_recovery = DeathRecoveryConfig(
            enabled=bool(death_raw.get("enabled", False)),
            threshold=death_threshold,
            town_respawn_template_path=str(death_raw.get("town_respawn_template_path", "assets/death/town_respawn.png")),
        )
        return AppConfig(
            target_window_title=str(raw["target_window_title"]),
            capture=CaptureConfig(**raw["capture"]),
            detection=DetectionConfig(template_paths, negative_template_paths, threshold, tuple(roi) if roi else None, center_roi),
            action=ActionConfig(
                key=str(action["key"]),
                dry_run=bool(action["dry_run"]),
                key_hold_ms=int(action["key_hold_ms"]),
                repeat_interval_ms=int(action["repeat_interval_ms"]),
            ),
            pointer=PointerConfig(offset_y=int(raw["pointer"]["offset_y"])),
            center_target=CenterTargetConfig(
                enabled=bool(raw["center_target"].get("enabled", True)),
                template_paths=tuple(str(value) for value in raw["center_target"]["template_paths"]),
                radius_px=int(raw["center_target"]["radius_px"]),
                key=str(raw["center_target"]["key"]),
                key_hold_ms=int(raw["center_target"]["key_hold_ms"]),
                repeat_interval_ms=int(raw["center_target"]["repeat_interval_ms"]),
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
            town_teleport=town_teleport,
            death_recovery=death_recovery,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"設定檔格式錯誤：{error}") from error
