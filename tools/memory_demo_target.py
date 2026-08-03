"""Write simulated game-state data to an authorized shared-memory segment."""

from __future__ import annotations

import math
import sys
import time
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from screen_automation.memory_demo import DemoMonster, DemoSnapshot, SHARED_MEMORY_NAME, SHARED_MEMORY_SIZE, write_snapshot


def main() -> None:
    shared_memory = SharedMemory(name=SHARED_MEMORY_NAME, create=True, size=SHARED_MEMORY_SIZE)
    print(f"Demo target started: {SHARED_MEMORY_NAME}. Press Ctrl+C to stop.")
    started_at = time.monotonic()
    try:
        while True:
            elapsed = time.monotonic() - started_at
            snapshot = DemoSnapshot(0.0, 0.0, True, (
                DemoMonster("slime-a", 40 + 20 * math.sin(elapsed), 25, 100),
                DemoMonster("slime-b", -70, 55 + 10 * math.cos(elapsed), 70),
                DemoMonster("slime-c", 180, -40, 40),
            ))
            write_snapshot(shared_memory, snapshot)
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        shared_memory.close()
        shared_memory.unlink()


if __name__ == "__main__":
    main()
