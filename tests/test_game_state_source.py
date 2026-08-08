import json
import socket
import time
import unittest

from src.screen_automation.game_state_source import GameStateSource
from tests.test_game_state import valid_snapshot_payload


def encode(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


class GameStateSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = GameStateSource("127.0.0.1", 0, stale_after_ms=100)
        self.source.start()

    def tearDown(self) -> None:
        self.source.stop()

    def _send(self, payload: bytes) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(payload, self.source.address)

    def _wait_for_latest(self):
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            snapshot = self.source.latest()
            if snapshot is not None:
                return snapshot
            time.sleep(0.005)
        self.fail("source did not receive a valid snapshot")

    def test_receives_latest_snapshot_on_background_thread(self) -> None:
        self._send(encode(valid_snapshot_payload()))

        snapshot = self._wait_for_latest()

        self.assertEqual(snapshot.sequence, 42)

    def test_malformed_datagram_does_not_replace_latest_snapshot(self) -> None:
        self._send(encode(valid_snapshot_payload()))
        first = self._wait_for_latest()

        self._send(b"not-json")
        time.sleep(0.03)

        self.assertIs(self.source.latest(), first)

    def test_latest_returns_none_after_local_receive_time_expires(self) -> None:
        self._send(encode(valid_snapshot_payload()))
        self._wait_for_latest()

        time.sleep(0.12)

        self.assertIsNone(self.source.latest())

    def test_stop_releases_udp_port(self) -> None:
        address = self.source.address
        self.source.stop()

        replacement = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addCleanup(replacement.close)
        replacement.bind(address)


if __name__ == "__main__":
    unittest.main()
