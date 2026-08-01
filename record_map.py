from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime
from pathlib import Path

import mss
import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from screen_automation.config import CaptureConfig, load_config
from screen_automation.map_recording import MapRecorder
from screen_automation.navigation import minimap_bounds
from screen_automation.window import WindowInfo, capture_print_window, find_window


def capture_window(window: WindowInfo, capture: CaptureConfig) -> np.ndarray:
    if capture.method == "printwindow":
        try:
            return capture_print_window(window)
        except RuntimeError as error:
            if not capture.fallback_to_desktop:
                raise
            logging.warning("PrintWindow capture failed; using desktop capture: %s", error)
    with mss.mss() as sct:
        shot = sct.grab({"left": window.left, "top": window.top, "width": window.width, "height": window.height})
        return np.asarray(shot)[:, :, :3].copy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Record overlapping minimap frames without sending input")
    parser.add_argument("--config", default="config.yaml", help="configuration file")
    parser.add_argument("--seconds", type=float, default=30.0, help="recording duration")
    parser.add_argument("--interval-ms", type=int, default=250, help="frame sampling interval")
    parser.add_argument("--output", default=None, help="output directory; defaults to maps/<timestamp>")
    args = parser.parse_args()
    if args.seconds <= 0 or args.interval_ms <= 0:
        parser.error("--seconds and --interval-ms must be positive")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    output_dir = Path(args.output) if args.output else config_path.parent / "maps" / datetime.now().strftime("%Y%m%d_%H%M%S")
    recorder = MapRecorder()
    accepted = 0
    skipped = 0
    deadline = time.monotonic() + args.seconds
    logging.info("Map recording started; input is disabled for this command")
    while time.monotonic() < deadline:
        window = find_window(config.target_window_title)
        frame = capture_window(window, config.capture)
        route = config.walking.route
        left, top, width, height = minimap_bounds(
            frame.shape[1], frame.shape[0], route.minimap.right_px, route.minimap.top_px, route.minimap.width_px, route.minimap.height_px
        )
        if recorder.add_frame(frame[top:top + height, left:left + width]):
            accepted += 1
        else:
            skipped += 1
        time.sleep(args.interval_ms / 1000)
    manifest_path = recorder.write(output_dir)
    logging.info("Map recording saved; accepted=%s skipped=%s manifest=%s", accepted, skipped, manifest_path)


if __name__ == "__main__":
    main()
