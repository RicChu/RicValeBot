from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass(frozen=True)
class DetectionResult:
    score: float
    left: int
    top: int
    width: int
    height: int


class TemplateDetector:
    def __init__(self, template_path: Path, threshold: float, roi: tuple[int, int, int, int] | None) -> None:
        self.template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if self.template is None:
            raise FileNotFoundError(f"無法讀取範本圖片：{template_path}")
        self.threshold = threshold
        self.roi = roi

    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None:
        frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        offset_x = offset_y = 0
        search_area = frame_gray
        if self.roi:
            offset_x, offset_y, width, height = self.roi
            search_area = frame_gray[offset_y : offset_y + height, offset_x : offset_x + width]
        template_height, template_width = self.template.shape
        if search_area.shape[0] < template_height or search_area.shape[1] < template_width:
            raise ValueError("範本圖片大於設定的搜尋區域")
        result = cv2.matchTemplate(search_area, self.template, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(result)
        if score < self.threshold:
            return None
        return DetectionResult(float(score), location[0] + offset_x, location[1] + offset_y, template_width, template_height)


class MultiTemplateDetector:
    """從多張範本中取出相似度最高的合格結果。"""

    def __init__(self, template_paths: tuple[Path, ...], threshold: float, roi: tuple[int, int, int, int] | None) -> None:
        image_paths: list[Path] = []
        for path in template_paths:
            if path.is_dir():
                image_paths.extend(sorted(item for item in path.iterdir() if item.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}))
            else:
                image_paths.append(path)
        if not image_paths:
            raise FileNotFoundError("範本資料夾中沒有可用圖片")
        self.detectors = [TemplateDetector(path, threshold, roi) for path in image_paths]

    def detect(self, frame_bgr: np.ndarray) -> DetectionResult | None:
        matches = [match for detector in self.detectors if (match := detector.detect(frame_bgr)) is not None]
        return max(matches, key=lambda match: match.score) if matches else None
