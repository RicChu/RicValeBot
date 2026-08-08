import json
import math
import unittest

from src.screen_automation.game_state import decode_game_state, nearest_living_monster


def valid_snapshot_payload() -> dict:
    return {
        "schema_version": 1,
        "sequence": 42,
        "captured_at_unix_ms": 1_786_123_456_789,
        "map_id": "stormreef_isle",
        "player": {
            "character_id": "character-42",
            "x": 10.0,
            "y": 2.0,
            "z": 20.0,
            "health": 900,
            "max_health": 1000,
        },
        "monsters": [
            {
                "runtime_id": "far",
                "config_id": "scrapfang",
                "x": 30.0,
                "y": 2.0,
                "z": 20.0,
                "health": 300,
                "max_health": 300,
                "is_alive": True,
            },
            {
                "runtime_id": "near",
                "config_id": "scrapfang",
                "x": 13.0,
                "y": 2.0,
                "z": 24.0,
                "health": 0,
                "max_health": 300,
                "is_alive": False,
            },
        ],
        "inventory": {
            "equips": 12,
            "artifacts": 3,
            "cards": 8,
            "gems": 4,
            "junks": 15,
            "consumables": 6,
            "cosmetics": 2,
        },
        "equipped_ids": ["stormplate-shoes"],
        "artifact_ids": ["drooping-bat"],
    }


def encode(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class GameStateSnapshotTests(unittest.TestCase):
    def test_decodes_schema_v1_snapshot(self) -> None:
        snapshot = decode_game_state(encode(valid_snapshot_payload()))

        self.assertEqual(snapshot.schema_version, 1)
        self.assertEqual(snapshot.sequence, 42)
        self.assertEqual(snapshot.map_id, "stormreef_isle")
        self.assertEqual(snapshot.player.position.x, 10.0)
        self.assertEqual(snapshot.inventory.equips, 12)
        self.assertEqual(snapshot.equipped_ids, ("stormplate-shoes",))
        self.assertEqual(len(snapshot.monsters), 2)

    def test_rejects_unknown_schema_version(self) -> None:
        payload = valid_snapshot_payload()
        payload["schema_version"] = 2

        with self.assertRaisesRegex(ValueError, "schema_version"):
            decode_game_state(encode(payload))

    def test_rejects_non_finite_coordinates(self) -> None:
        payload = valid_snapshot_payload()
        payload["monsters"][0]["x"] = math.nan

        with self.assertRaisesRegex(ValueError, "finite"):
            decode_game_state(encode(payload))

    def test_selects_nearest_living_monster(self) -> None:
        payload = valid_snapshot_payload()
        payload["monsters"][1]["health"] = 10
        payload["monsters"][1]["is_alive"] = True
        snapshot = decode_game_state(encode(payload))

        target = nearest_living_monster(snapshot)

        self.assertIsNotNone(target)
        self.assertEqual(target.runtime_id, "near")


if __name__ == "__main__":
    unittest.main()
