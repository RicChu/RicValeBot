from __future__ import annotations

import cv2
import numpy as np

from .detector import DetectionResult


class HSVBarDetector:
    def __init__(
        self,
        min_width: int,
        max_height: int,
        min_aspect_ratio: float,
        max_width: int = 160,
        min_height: int = 12,
        max_aspect_ratio: float = 12.0,
        max_white_ratio: float = 0.80,
        min_horizontal_run_ratio: float = 0.65,
        min_allowed_colour_ratio: float = 0.60,
        edge_band_px: int = 2,
        edge_black_ratio: float = 0.50,
        inner_band_enabled: bool = True,
        black_residual_enabled: bool = False,
        black_residual_min_extent: float = 0.75,
        black_residual_dedup_iou: float = 0.30,
        black_residual_outer_ring_px: int = 3,
        black_residual_min_outer_contrast: float = 8.0,
        black_residual_low_colour_trigger_ratio: float = 0.15,
    ) -> None:
        self.min_width = min_width
        self.max_width = max_width
        self.min_height = min_height
        self.max_height = max_height
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.max_white_ratio = max_white_ratio
        self.min_horizontal_run_ratio = min_horizontal_run_ratio
        self.min_allowed_colour_ratio = min_allowed_colour_ratio
        self.edge_band_px = edge_band_px
        self.edge_black_ratio = edge_black_ratio
        self.inner_band_enabled = inner_band_enabled
        self.black_residual_enabled = black_residual_enabled
        self.black_residual_min_extent = black_residual_min_extent
        self.black_residual_dedup_iou = black_residual_dedup_iou
        self.black_residual_outer_ring_px = black_residual_outer_ring_px
        self.black_residual_min_outer_contrast = black_residual_min_outer_contrast
        self.black_residual_low_colour_trigger_ratio = black_residual_low_colour_trigger_ratio

    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None:
        candidates = self.detect_all(frame_bgr)
        return max(candidates, key=lambda item: item.score) if candidates else None

    @staticmethod
    def _has_horizontal_colour_run(colour_mask: np.ndarray, minimum_ratio: float) -> bool:
        minimum_width = int(np.ceil(colour_mask.shape[1] * minimum_ratio))
        consecutive_rows = 0
        for row in colour_mask:
            longest_run = current_run = 0
            for pixel in row:
                current_run = current_run + 1 if pixel else 0
                longest_run = max(longest_run, current_run)
            consecutive_rows = consecutive_rows + 1 if longest_run >= minimum_width else 0
            if consecutive_rows >= 3:
                return True
        return False

    @staticmethod
    def _has_black_edges_around_inner_band(
        black_mask: np.ndarray,
        seed_left: int,
        seed_top: int,
        seed_width: int,
        seed_height: int,
        band_height: int,
        minimum_ratio: float,
    ) -> bool:
        """Confirm the thin black edge immediately next to the coloured inner band.

        The previous check looked outside the expanded candidate rectangle.  On
        the game UI the black edge is part of that rectangle, so a one-pixel
        frame over a dim background was incorrectly rejected.
        """
        if seed_top < band_height or seed_top + seed_height + band_height > black_mask.shape[0]:
            return False
        # Measure across the actual colour band.  Including the horizontal
        # expansion would dilute a one-pixel frame with the dim background.
        left = seed_left
        right = seed_left + seed_width
        top_band = black_mask[seed_top - band_height:seed_top, left:right]
        bottom_band = black_mask[seed_top + seed_height:seed_top + seed_height + band_height, left:right]
        return (
            cv2.countNonZero(top_band) / top_band.size >= minimum_ratio
            and cv2.countNonZero(bottom_band) / bottom_band.size >= minimum_ratio
        )

    @staticmethod
    def _allowed_colour_ratio(allowed: np.ndarray, left: int, top: int, width: int, height: int) -> float:
        """Return the red/white/black coverage of one small candidate box."""
        return cv2.countNonZero(allowed[top:top + height, left:left + width]) / (width * height)

    @staticmethod
    def _overlaps_any(candidate: DetectionResult, existing: list[DetectionResult], minimum_iou: float) -> bool:
        candidate_area = candidate.width * candidate.height
        for item in existing:
            left = max(candidate.left, item.left)
            top = max(candidate.top, item.top)
            right = min(candidate.left + candidate.width, item.left + item.width)
            bottom = min(candidate.top + candidate.height, item.top + item.height)
            if right <= left or bottom <= top:
                continue
            intersection = (right - left) * (bottom - top)
            union = candidate_area + item.width * item.height - intersection
            if union and intersection / union >= minimum_iou:
                return True
        return False

    @staticmethod
    def _has_outer_contrast(
        gray: np.ndarray, left: int, top: int, width: int, height: int, ring_px: int, minimum_contrast: float
    ) -> bool:
        image_height, image_width = gray.shape
        if left < ring_px or top < ring_px or left + width + ring_px > image_width or top + height + ring_px > image_height:
            return False
        inner_mean = gray[top:top + height, left:left + width].mean()
        outer = gray[top - ring_px:top + height + ring_px, left - ring_px:left + width + ring_px].astype(np.float32)
        ring = np.ones(outer.shape, dtype=bool)
        ring[ring_px:ring_px + height, ring_px:ring_px + width] = False
        return abs(float(outer[ring].mean()) - float(inner_mean)) >= minimum_contrast

    def _detect_by_black_residual(
        self,
        frame_bgr: np.ndarray,
        red: np.ndarray,
        white: np.ndarray,
        black: np.ndarray,
        existing: list[DetectionResult],
    ) -> list[DetectionResult]:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        candidates: list[DetectionResult] = []
        image_height, image_width = black.shape
        coloured = red | white
        allowed = black | coloured
        for contour in cv2.findContours(black, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            left, top, width, height = cv2.boundingRect(contour)
            aspect_ratio = width / max(height, 1)
            if (
                not self.min_width <= width <= self.max_width
                or not self.min_height <= height <= self.max_height
                or not self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio
                or left == 0 or top == 0 or left + width >= image_width or top + height >= image_height
                or cv2.contourArea(contour) / (width * height) < self.black_residual_min_extent
            ):
                continue
            allowed_ratio = self._allowed_colour_ratio(allowed, left, top, width, height)
            coloured_ratio = cv2.countNonZero(coloured[top:top + height, left:left + width]) / (width * height)
            if (
                allowed_ratio < self.min_allowed_colour_ratio
                or coloured_ratio > self.black_residual_low_colour_trigger_ratio
            ):
                continue
            result = DetectionResult(float(1 - coloured_ratio), left, top, width, height)
            if self._overlaps_any(result, existing + candidates, self.black_residual_dedup_iou):
                continue
            if self._has_outer_contrast(
                gray,
                left,
                top,
                width,
                height,
                self.black_residual_outer_ring_px,
                self.black_residual_min_outer_contrast,
            ):
                candidates.append(result)
        return candidates

    def _detect_by_inner_band(
        self, frame_bgr: np.ndarray, red: np.ndarray, black: np.ndarray, white: np.ndarray
    ) -> list[DetectionResult]:
        candidates: list[DetectionResult] = []
        coloured = red | white
        allowed = red | white | black
        for contour in cv2.findContours(coloured, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            seed_left, seed_top, seed_width, seed_height = cv2.boundingRect(contour)
            if (
                seed_width < max(20, int(np.ceil(self.min_width * 0.40)))
                or not 3 <= seed_height <= max(6, self.max_height // 2)
                or seed_width / seed_height < max(4.0, self.min_aspect_ratio)
                or not self._has_horizontal_colour_run(
                    coloured[seed_top:seed_top + seed_height, seed_left:seed_left + seed_width],
                    self.min_horizontal_run_ratio,
                )
            ):
                continue
            border_x, border_y = 4, 3
            left = max(0, seed_left - border_x)
            top = max(0, seed_top - border_y)
            right = min(frame_bgr.shape[1], seed_left + seed_width + border_x)
            bottom = min(frame_bgr.shape[0], seed_top + seed_height + border_y)
            width, height = right - left, bottom - top
            aspect_ratio = width / max(height, 1)
            if (
                not self.min_width <= width <= self.max_width
                or not self.min_height <= height <= self.max_height
                or not self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio
                or not self._has_black_edges_around_inner_band(
                    black,
                    seed_left,
                    seed_top,
                    seed_width,
                    seed_height,
                    self.edge_band_px,
                    self.edge_black_ratio,
                )
            ):
                continue
            # Validate only the tight inner strip plus its verified black
            # edges.  The larger geometry box intentionally has some slack,
            # which can otherwise include unrelated dark game background.
            composition_top = seed_top - self.edge_band_px
            composition_height = seed_height + 2 * self.edge_band_px
            if self._allowed_colour_ratio(
                allowed, seed_left, composition_top, seed_width, composition_height
            ) < self.min_allowed_colour_ratio:
                continue
            white_ratio = cv2.countNonZero(
                white[composition_top:composition_top + composition_height, seed_left:seed_left + seed_width]
            ) / (seed_width * composition_height)
            if white_ratio <= self.max_white_ratio:
                candidates.append(DetectionResult(float(1 - white_ratio), left, top, width, height))
        return candidates

    def detect_all(self, frame_bgr: np.ndarray) -> tuple[DetectionResult, ...]:
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        # OpenCV HSV values calibrated from supplied UI colours:
        # #FF0073 -> (166, 255, 255), #0F1016 -> (116, 81, 22), #FFFFFF -> (0, 0, 255).
        red = cv2.inRange(hsv, (158, 145, 100), (176, 255, 255))
        black = cv2.inRange(hsv, (0, 0, 0), (179, 255, 45))
        white = cv2.inRange(hsv, (0, 0, 235), (179, 25, 255))
        candidates: list[DetectionResult] = []
        if self.inner_band_enabled:
            candidates.extend(self._detect_by_inner_band(frame_bgr, red, black, white))
        if self.black_residual_enabled:
            candidates.extend(self._detect_by_black_residual(frame_bgr, red, white, black, candidates))
        return tuple(sorted(candidates, key=lambda item: (item.top, item.left)))
        # 先連接斷續的黑框邊線，再以黑框的外接矩形作為候選長條。
        outline = cv2.morphologyEx(black, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        candidates: list[DetectionResult] = []
        for contour in cv2.findContours(outline, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            left, top, width, height = cv2.boundingRect(contour)
            aspect_ratio = width / max(height, 1)
            if (
                not self.min_width <= width <= self.max_width
                or not self.min_height <= height <= self.max_height
                or not self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio
            ):
                continue
            margin = min(4, (width - 1) // 2, (height - 1) // 2)
            inner_area = (width - 2 * margin) * (height - 2 * margin)
            inner_slice = np.s_[top + margin:top + height - margin, left + margin:left + width - margin]
            allowed = red | white | black
            inner_allowed = allowed[inner_slice]
            allowed_colour_ratio = cv2.countNonZero(inner_allowed) / inner_area
            white_ratio = cv2.countNonZero(white[inner_slice]) / inner_area
            coloured_content = red[inner_slice] | white[inner_slice]
            if (
                self.min_allowed_colour_ratio <= allowed_colour_ratio
                and white_ratio <= self.max_white_ratio
                and cv2.countNonZero(coloured_content) > 0
                and self._has_horizontal_colour_run(inner_allowed, self.min_horizontal_run_ratio)
            ):
                candidates.append(DetectionResult(float(allowed_colour_ratio + (1 - white_ratio)), left, top, width, height))

        return tuple(sorted(candidates, key=lambda item: (item.top, item.left)))
