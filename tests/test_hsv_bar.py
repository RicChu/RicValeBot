import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.hsv_bar import HSVBarDetector
from screen_automation.config import load_config


class HSVBarTests(unittest.TestCase):
    def test_configured_black_residual_path_bridges_a_thirty_percent_red_bar(self) -> None:
        """A partially depleted bar must not fall in the two detector paths' gap."""
        config = load_config(Path(__file__).parents[1] / "config.yaml")
        settings = config.hsv_bar
        residual = settings.black_residual
        detector = HSVBarDetector(
            min_width=settings.min_width,
            max_width=settings.max_width,
            min_height=settings.min_height,
            max_height=settings.max_height,
            min_aspect_ratio=settings.min_aspect_ratio,
            max_aspect_ratio=settings.max_aspect_ratio,
            max_white_ratio=settings.max_white_ratio,
            min_horizontal_run_ratio=settings.min_horizontal_run_ratio,
            min_allowed_colour_ratio=settings.min_allowed_colour_ratio,
            edge_band_px=settings.edge_band_px,
            edge_black_ratio=settings.edge_black_ratio,
            inner_band_enabled=settings.inner_band_enabled,
            black_residual_enabled=settings.black_residual_enabled,
            black_residual_min_extent=residual.min_extent,
            black_residual_dedup_iou=residual.dedup_iou,
            black_residual_outer_ring_px=residual.outer_ring_px,
            black_residual_min_outer_contrast=residual.min_outer_contrast,
            black_residual_low_colour_trigger_ratio=residual.low_colour_trigger_ratio,
        )
        frame = np.full((80, 160, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (30, 30), (120, 45), (22, 16, 15), -1)
        cv2.rectangle(frame, (34, 33), (58, 42), (115, 0, 255), -1)

        self.assertEqual(len(detector.detect_all(frame)), 1)

    def test_returns_all_separate_black_outlined_bars(self) -> None:
        frame = np.full((180, 260, 3), 80, dtype=np.uint8)
        for top in (20, 70, 120):
            cv2.rectangle(frame, (50, top), (190, top + 15), (22, 16, 15), -1)
            cv2.rectangle(frame, (54, top + 3), (125, top + 12), (115, 0, 255), -1)
            cv2.rectangle(frame, (126, top + 3), (185, top + 12), (255, 255, 255), -1)
        detector = HSVBarDetector(min_width=60, max_height=30, min_aspect_ratio=4.0)

        results = detector.detect_all(frame)

        self.assertEqual(len(results), 3)
        self.assertEqual([result.top for result in results], [20, 70, 120])
    def test_detects_a_thin_red_white_black_bar(self) -> None:
        frame = np.full((120, 240, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (50, 45), (190, 60), (22, 16, 15), -1)
        cv2.rectangle(frame, (54, 48), (125, 57), (115, 0, 255), -1)
        cv2.rectangle(frame, (126, 48), (185, 57), (255, 255, 255), -1)
        detector = HSVBarDetector(min_width=60, max_height=30, min_aspect_ratio=4.0)

        result = detector.detect(frame)

        self.assertIsNotNone(result)
        self.assertLessEqual(abs(result.left - 50), 2)
        self.assertLessEqual(abs(result.top - 45), 2)

    def test_rejects_orange_red_content_outside_the_configured_pink_red_range(self) -> None:
        frame = np.full((120, 240, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (50, 45), (190, 60), (22, 16, 15), -1)
        cv2.rectangle(frame, (54, 48), (185, 57), (0, 64, 255), -1)
        detector = HSVBarDetector(min_width=60, max_height=30, min_aspect_ratio=4.0)

        self.assertIsNone(detector.detect(frame))

    def test_ignores_large_black_background_without_red_or_white_bar_content(self) -> None:
        frame = np.zeros((120, 240, 3), dtype=np.uint8)
        detector = HSVBarDetector(min_width=60, max_height=30, min_aspect_ratio=4.0)

        self.assertIsNone(detector.detect(frame))

    def test_rejects_red_bar_without_a_black_outline(self) -> None:
        frame = np.full((100, 220, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (50, 40), (180, 52), (90, 20, 255), -1)
        detector = HSVBarDetector(min_width=60, max_height=30, min_aspect_ratio=4.0)

        self.assertIsNone(detector.detect(frame))

    def test_accepts_a_compact_black_outlined_bar(self) -> None:
        frame = np.full((120, 240, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (60, 45), (150, 69), (0, 0, 0), -1)
        cv2.rectangle(frame, (64, 49), (125, 56), (115, 0, 255), -1)
        cv2.rectangle(frame, (64, 59), (145, 65), (255, 255, 255), -1)
        detector = HSVBarDetector(min_width=60, max_height=35, min_aspect_ratio=3.0)

        result = detector.detect(frame)

        self.assertIsNotNone(result)
        self.assertLessEqual(abs(result.left - 60), 2)
        self.assertLessEqual(abs(result.top - 45), 2)

    def test_rejects_a_gray_filled_black_rectangle(self) -> None:
        frame = np.full((120, 280, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (50, 40), (180, 64), (0, 0, 0), -1)
        cv2.rectangle(frame, (54, 44), (176, 60), (170, 170, 170), -1)
        detector = HSVBarDetector(min_width=60, max_height=35, min_aspect_ratio=3.0)

        self.assertIsNone(detector.detect(frame))

    def test_rejects_a_black_framed_bar_with_more_than_eighty_percent_white_inside(self) -> None:
        frame = np.full((120, 280, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (50, 40), (180, 64), (0, 0, 0), -1)
        cv2.rectangle(frame, (54, 44), (176, 60), (255, 255, 255), -1)
        detector = HSVBarDetector(min_width=60, max_height=35, min_aspect_ratio=3.0)

        self.assertIsNone(detector.detect(frame))

    def test_rejects_a_black_framed_bar_with_an_all_black_interior(self) -> None:
        frame = np.full((120, 280, 3), 80, dtype=np.uint8)
        cv2.rectangle(frame, (50, 40), (180, 64), (0, 0, 0), -1)
        detector = HSVBarDetector(min_width=60, max_height=35, min_aspect_ratio=3.0)

        self.assertIsNone(detector.detect(frame))

    def test_detects_a_pink_bar_when_its_black_outline_merges_into_a_dark_background(self) -> None:
        frame = np.full((120, 280, 3), (22, 16, 15), dtype=np.uint8)
        cv2.rectangle(frame, (54, 48), (123, 52), (115, 0, 255), -1)
        detector = HSVBarDetector(
            min_width=60, min_height=8, max_height=35, min_aspect_ratio=3.0
        )

        result = detector.detect(frame)

        self.assertIsNotNone(result)
        self.assertLessEqual(abs((result.left + result.width // 2) - 89), 2)
        self.assertLessEqual(abs((result.top + result.height // 2) - 50), 2)

    def test_detects_a_thin_pink_bar_with_one_pixel_black_edges(self) -> None:
        """The game can render a one-pixel black edge over a dim background."""
        frame = np.full((100, 220, 3), 55, dtype=np.uint8)
        cv2.rectangle(frame, (60, 39), (140, 45), (22, 16, 15), -1)
        cv2.rectangle(frame, (60, 40), (140, 44), (115, 0, 255), -1)
        detector = HSVBarDetector(
            min_width=60, min_height=8, max_height=35, min_aspect_ratio=3.0
        )

        result = detector.detect(frame)

        self.assertIsNotNone(result)
        self.assertLessEqual(abs((result.left + result.width // 2) - 100), 2)

    def test_uses_allowed_colour_ratio_to_reject_a_noisy_candidate_box(self) -> None:
        frame = np.full((100, 220, 3), 80, dtype=np.uint8)
        # A valid-looking three-row bar whose contour is artificially extended
        # by a thin red effect.  Its local red/white/black composition is too
        # low for a real compact bar.
        cv2.rectangle(frame, (60, 43), (140, 44), (22, 16, 15), -1)
        cv2.rectangle(frame, (60, 45), (140, 49), (115, 0, 255), -1)
        cv2.rectangle(frame, (100, 49), (100, 61), (115, 0, 255), -1)
        cv2.rectangle(frame, (60, 62), (140, 63), (22, 16, 15), -1)
        detector = HSVBarDetector(
            min_width=60, min_height=8, max_height=35, min_aspect_ratio=3.0,
            min_allowed_colour_ratio=0.60,
        )

        self.assertIsNone(detector.detect(frame))

    def test_allows_inner_band_and_black_residual_paths_to_be_enabled_independently(self) -> None:
        coloured_frame = np.full((120, 240, 3), 80, dtype=np.uint8)
        cv2.rectangle(coloured_frame, (60, 45), (150, 60), (22, 16, 15), -1)
        cv2.rectangle(coloured_frame, (64, 48), (145, 57), (115, 0, 255), -1)
        black_frame = np.full((120, 240, 3), 80, dtype=np.uint8)
        cv2.rectangle(black_frame, (60, 45), (150, 60), (22, 16, 15), -1)

        def detector(inner_band_enabled: bool, black_residual_enabled: bool) -> HSVBarDetector:
            item = HSVBarDetector(
                min_width=60, min_height=8, max_height=35, min_aspect_ratio=3.0
            )
            item.inner_band_enabled = inner_band_enabled
            item.black_residual_enabled = black_residual_enabled
            return item

        self.assertEqual(len(detector(True, False).detect_all(coloured_frame)), 1)
        self.assertEqual(len(detector(False, True).detect_all(coloured_frame)), 0)
        self.assertEqual(len(detector(True, False).detect_all(black_frame)), 0)
        self.assertEqual(len(detector(False, True).detect_all(black_frame)), 1)


if __name__ == "__main__":
    unittest.main()
