import json
import math
import socket
import unittest

from src.screen_automation.game_state import decode_game_state, nearest_living_monster, receive_game_state


def valid_snapshot_payload() -> dict:
    return {
        "schema_version": 2,
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
                "viewport_x": 0.75,
                "viewport_y": 0.40,
                "viewport_depth": 15.0,
                "view_x": 4.0,
                "view_z": 15.0,
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
                "viewport_x": 0.55,
                "viewport_y": 0.45,
                "viewport_depth": 5.0,
                "view_x": 1.0,
                "view_z": 5.0,
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
    def test_decodes_schema_v2_snapshot_with_camera_projection(self) -> None:
        snapshot = decode_game_state(encode(valid_snapshot_payload()))

        self.assertEqual(snapshot.schema_version, 2)
        self.assertEqual(snapshot.sequence, 42)
        self.assertEqual(snapshot.map_id, "stormreef_isle")
        self.assertEqual(snapshot.player.position.x, 10.0)
        self.assertEqual(snapshot.inventory.equips, 12)
        self.assertEqual(snapshot.equipped_ids, ("stormplate-shoes",))
        self.assertEqual(len(snapshot.monsters), 2)
        self.assertEqual(snapshot.monsters[0].viewport_x, 0.75)
        self.assertEqual(snapshot.monsters[0].viewport_y, 0.40)
        self.assertEqual(snapshot.monsters[0].viewport_depth, 15.0)
        self.assertEqual(snapshot.monsters[0].view_x, 4.0)
        self.assertEqual(snapshot.monsters[0].view_z, 15.0)

    def test_rejects_unknown_schema_version(self) -> None:
        payload = valid_snapshot_payload()
        payload["schema_version"] = 1

        with self.assertRaisesRegex(ValueError, "schema_version"):
            decode_game_state(encode(payload))

    def test_rejects_non_finite_coordinates(self) -> None:
        payload = valid_snapshot_payload()
        payload["monsters"][0]["x"] = math.nan

        with self.assertRaisesRegex(ValueError, "finite"):
            decode_game_state(encode(payload))

    def test_rejects_non_finite_camera_coordinates(self) -> None:
        payload = valid_snapshot_payload()
        payload["monsters"][0]["view_x"] = math.inf

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

    def test_udp_receiver_skips_malformed_datagram(self) -> None:
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addCleanup(receiver.close)
        self.addCleanup(sender.close)
        receiver.bind(("127.0.0.1", 0))
        receiver.settimeout(1.0)
        destination = receiver.getsockname()
        sender.sendto(b"not-json", destination)
        sender.sendto(encode(valid_snapshot_payload()), destination)

        snapshot = receive_game_state(receiver)

        self.assertEqual(snapshot.sequence, 42)


if __name__ == "__main__":
    unittest.main()
