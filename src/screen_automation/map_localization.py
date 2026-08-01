from __future__ import annotations

from math import hypot
from pathlib import Path

import cv2
import numpy as np

from .map_recording import MapFrame, estimate_translation_with_inliers, load_manifest


class MapLocalizer:
    """Locates a live minimap in the pixel coordinate system of a recorded map."""

    def __init__(self, manifest_path: Path, min_match_count: int, max_position_jump_px: int) -> None:
        self.manifest = load_manifest(manifest_path)
        self.min_match_count = min_match_count
        self.max_position_jump_px = max_position_jump_px
        self._frames: tuple[tuple[MapFrame, np.ndarray], ...] = tuple(
            (frame, image)
            for frame in self.manifest.frames
            if (image := cv2.imread(str(manifest_path.parent / frame.image_path), cv2.IMREAD_COLOR)) is not None
        )
        if not self._frames:
            raise ValueError("recorded map manifest has no readable frames")
        self._last_position: tuple[int, int] | None = None

    def locate(self, minimap: np.ndarray) -> tuple[int, int] | None:
        candidates: list[tuple[int, tuple[int, int]]] = []
        for frame, reference in self._frames:
            result = estimate_translation_with_inliers(reference, minimap)
            if result is None:
                continue
            shift_x, shift_y, inliers = result
            if inliers >= self.min_match_count:
                # The live map pixels move in the inverse direction of the viewport.
                candidates.append((inliers, (frame.x - shift_x, frame.y - shift_y)))
        if not candidates:
            return None
        _, position = max(candidates, key=lambda candidate: candidate[0])
        if self._last_position and hypot(position[0] - self._last_position[0], position[1] - self._last_position[1]) > self.max_position_jump_px:
            return None
        self._last_position = position
        return position
