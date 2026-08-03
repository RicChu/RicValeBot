"""Read the authorized shared-memory demo and print targeting decisions."""

from __future__ import annotations

import time
import sys
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from screen_automation.memory_demo import SHARED_MEMORY_NAME, choose_nearest_monster, count_nearby_monsters, read_snapshot


def main() -> None:
    try:
        shared_memory = SharedMemory(name=SHARED_MEMORY_NAME, create=False)
    except FileNotFoundError:
        print("Demo target is not running. Start tools/memory_demo_target.py first.")
        return
    try:
        while True:
            if snapshot := read_snapshot(shared_memory):
                target = choose_nearest_monster(snapshot)
                crowd = count_nearby_monsters(snapshot, radius=100)
                print(f"combat={snapshot.in_combat} target={target.monster_id if target else None} crowd={crowd}")
            time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        shared_memory.close()


if __name__ == "__main__":
    main()
