from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml


@dataclass(frozen=True)
class MapFrame:
    index: int
    x: int
    y: int
    image_path: str


@dataclass(frozen=True)
class MapManifest:
    """Recorded-map metadata. Frame positions and route points use canvas pixels."""

    origin_x: int
    origin_y: int
    width: int
    height: int
    frames: tuple[MapFrame, ...]

    def global_position(self, minimap_origin: tuple[int, int], marker_position: tuple[int, int]) -> tuple[int, int]:
        return minimap_origin[0] + marker_position[0], minimap_origin[1] + marker_position[1]


def estimate_translation(previous: np.ndarray, current: np.ndarray) -> tuple[int, int] | None:
    """Return the feature movement from ``previous`` pixels to ``current`` pixels."""
    result = estimate_translation_with_inliers(previous, current)
    return (result[0], result[1]) if result else None


def estimate_translation_with_inliers(previous: np.ndarray, current: np.ndarray) -> tuple[int, int, int] | None:
    """Return pixel translation and RANSAC inlier count for two overlapping images."""
    previous_gray = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=1200)
    previous_points, previous_descriptors = orb.detectAndCompute(previous_gray, None)
    current_points, current_descriptors = orb.detectAndCompute(current_gray, None)
    if previous_descriptors is None or current_descriptors is None:
        return None

    matches = cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(previous_descriptors, current_descriptors, k=2)
    good_matches = [pair[0] for pair in matches if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance]
    if len(good_matches) < 6:
        return None
    source = np.float32([previous_points[match.queryIdx].pt for match in good_matches]).reshape(-1, 1, 2)
    destination = np.float32([current_points[match.trainIdx].pt for match in good_matches]).reshape(-1, 1, 2)
    matrix, inliers = cv2.estimateAffinePartial2D(source, destination, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if matrix is None or inliers is None or int(inliers.sum()) < 6:
        return None
    return round(float(matrix[0, 2])), round(float(matrix[1, 2])), int(inliers.sum())


class MapRecorder:
    """Build a map canvas from consecutive, overlapping minimap images."""

    def __init__(self) -> None:
        self._images: list[np.ndarray] = []
        self._positions: list[tuple[int, int]] = []

    def add_frame(self, minimap: np.ndarray) -> bool:
        image = minimap.copy()
        if not self._images:
            self._images.append(image)
            self._positions.append((0, 0))
            return True
        translation = estimate_translation(self._images[-1], image)
        if translation is None:
            return False
        previous_x, previous_y = self._positions[-1]
        self._images.append(image)
        # Moving map pixels left means the player's viewport has moved right.
        self._positions.append((previous_x - translation[0], previous_y - translation[1]))
        return True

    def write(self, output_dir: Path) -> Path:
        if not self._images:
            raise ValueError("cannot write an empty map recording")
        output_dir.mkdir(parents=True, exist_ok=True)
        frames_dir = output_dir / "frames"
        frames_dir.mkdir(exist_ok=True)
        image_height, image_width = self._images[0].shape[:2]
        min_x = min(position[0] for position in self._positions)
        min_y = min(position[1] for position in self._positions)
        max_x = max(position[0] + image_width for position in self._positions)
        max_y = max(position[1] + image_height for position in self._positions)
        canvas = np.zeros((max_y - min_y, max_x - min_x, 3), dtype=np.uint8)
        frames: list[MapFrame] = []
        for index, (image, (raw_x, raw_y)) in enumerate(zip(self._images, self._positions, strict=True)):
            x, y = raw_x - min_x, raw_y - min_y
            canvas[y:y + image_height, x:x + image_width] = np.maximum(canvas[y:y + image_height, x:x + image_width], image)
            relative_path = Path("frames") / f"frame_{index:04d}.png"
            cv2.imwrite(str(output_dir / relative_path), image)
            frames.append(MapFrame(index=index, x=x, y=y, image_path=relative_path.as_posix()))
        cv2.imwrite(str(output_dir / "recorded_map.png"), canvas)
        manifest = MapManifest(origin_x=-min_x, origin_y=-min_y, width=canvas.shape[1], height=canvas.shape[0], frames=tuple(frames))
        manifest_path = output_dir / "manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(_manifest_data(manifest), sort_keys=False), encoding="utf-8")
        return manifest_path


def _manifest_data(manifest: MapManifest) -> dict[str, object]:
    return {
        "origin_x": manifest.origin_x,
        "origin_y": manifest.origin_y,
        "width": manifest.width,
        "height": manifest.height,
        "frames": [
            {"index": frame.index, "x": frame.x, "y": frame.y, "image_path": frame.image_path}
            for frame in manifest.frames
        ],
    }


def load_manifest(path: Path) -> MapManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return MapManifest(
        origin_x=int(raw["origin_x"]),
        origin_y=int(raw["origin_y"]),
        width=int(raw["width"]),
        height=int(raw["height"]),
        frames=tuple(
            MapFrame(index=int(frame["index"]), x=int(frame["x"]), y=int(frame["y"]), image_path=str(frame["image_path"]))
            for frame in raw["frames"]
        ),
    )
