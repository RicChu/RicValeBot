from __future__ import annotations

from .config import CenterROIConfig
from .detector import DetectionResult


def center_roi_bounds(frame_width: int, frame_height: int, config: CenterROIConfig) -> tuple[int, int, int, int]:
    """Return a center-biased ROI that is always contained by the frame."""
    if not config.enabled:
        return 0, 0, frame_width, frame_height

    width = min(config.width, frame_width)
    height = min(config.height, frame_height)
    left = (frame_width - width) // 2
    top = (frame_height - height) // 2 + config.offset_y
    top = max(0, min(frame_height - height, top))
    return left, top, width, height


def translate_detection(detection: DetectionResult, left: int, top: int) -> DetectionResult:
    """Convert a detection local to an ROI back to full-frame coordinates."""
    return DetectionResult(
        score=detection.score,
        left=detection.left + left,
        top=detection.top + top,
        width=detection.width,
        height=detection.height,
    )
