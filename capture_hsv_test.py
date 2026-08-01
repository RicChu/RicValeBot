"""連續擷取 HSV 診斷資料，不發送任何滑鼠或鍵盤輸入。"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from screen_automation.app import AutomationApp
from screen_automation.config import load_config
from screen_automation.window import find_window


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=5.0)
    parser.add_argument("--interval-ms", type=float, default=20.0)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    config = load_config(root / "config.yaml")
    app = AutomationApp(config, root)
    if app.hsv_detector is None:
        raise RuntimeError("請在 config.yaml 將 hsv_bar.enabled 設為 true")

    output = root / "debug" / f"hsv_capture_{datetime.now():%Y%m%d_%H%M%S}"
    output.mkdir(parents=True)
    interval = args.interval_ms / 1000
    started = time.perf_counter()
    rows: list[list[object]] = []
    index = 0
    while time.perf_counter() - started < args.seconds:
        scheduled = started + index * interval
        window = find_window(config.target_window_title)
        frame = app.capture(window)
        match = app.hsv_detector.detect(frame)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        filename = f"frame_{index:04d}.png"
        if match:
            cv2.rectangle(frame, (match.left, match.top), (match.left + match.width, match.top + match.height), (0, 255, 0), 2)
            rows.append([index, elapsed_ms, filename, 1, f"{match.score:.3f}", match.left, match.top, match.width, match.height])
        else:
            rows.append([index, elapsed_ms, filename, 0, "", "", "", "", ""])
        cv2.imwrite(str(output / filename), frame)
        index += 1
        time.sleep(max(0, scheduled + interval - time.perf_counter()))
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["frame", "elapsed_ms", "file", "detected", "score", "left", "top", "width", "height"])
        writer.writerows(rows)
    print(f"output={output}")
    print(f"frames={len(rows)}, detected={sum(row[3] for row in rows)}")


if __name__ == "__main__":
    main()
