"""背景畫面偵測與按鍵自動化的命令列入口。"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

# 讓專案在尚未封裝／安裝時也能直接以 `python main.py` 執行。
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from screen_automation.app import AutomationApp
from screen_automation.config import load_config


def main() -> None:
    parser = argparse.ArgumentParser(description="以模板比對監測 Windows 視窗並觸發按鍵")
    parser.add_argument("--config", default="config.yaml", help="設定檔路徑")
    parser.add_argument("--once", action="store_true", help="只執行一次偵測")
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    logging.basicConfig(
        level={"off": logging.ERROR, "events": logging.INFO, "diagnostic": logging.DEBUG}[config.runtime.log_mode],
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    app = AutomationApp(config, base_dir=config_path.parent)
    try:
        app.run(once=args.once)
    except KeyboardInterrupt:
        app.stop()
        logging.info("已停止；WASD 按鍵已釋放")


if __name__ == "__main__":
    main()
