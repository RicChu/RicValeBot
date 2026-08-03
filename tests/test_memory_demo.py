import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from screen_automation.memory_demo import DemoMonster, DemoSnapshot, choose_nearest_monster, count_nearby_monsters, decode_snapshot, encode_snapshot


class MemoryDemoTests(unittest.TestCase):
    def test_serializes_and_reads_a_snapshot_without_losing_monster_data(self) -> None:
        snapshot = DemoSnapshot(
            player_x=100.0,
            player_y=200.0,
            in_combat=True,
            monsters=(DemoMonster("bat-1", 125.0, 200.0, 80), DemoMonster("bat-2", 300.0, 200.0, 50)),
        )

        restored = decode_snapshot(encode_snapshot(snapshot))

        self.assertEqual(restored, snapshot)

    def test_selects_nearest_living_monster_and_counts_nearby_targets(self) -> None:
        snapshot = DemoSnapshot(
            player_x=0.0,
            player_y=0.0,
            in_combat=True,
            monsters=(
                DemoMonster("near", 30.0, 40.0, 10),
                DemoMonster("dead", 2.0, 2.0, 0),
                DemoMonster("far", 120.0, 0.0, 100),
            ),
        )

        self.assertEqual(choose_nearest_monster(snapshot).monster_id, "near")
        self.assertEqual(count_nearby_monsters(snapshot, radius=100.0), 1)


if __name__ == "__main__":
    unittest.main()
