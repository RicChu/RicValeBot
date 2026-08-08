"""Print read-only snapshots emitted by SpiritValeGameStateBridge."""

from __future__ import annotations

import argparse
import ipaddress
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.screen_automation.game_state import nearest_living_monster, receive_game_state


def loopback_address(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("host must be a loopback IP address") from exc
    if not address.is_loopback:
        raise argparse.ArgumentTypeError("host must be a loopback IP address")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Receive read-only SpiritVale game-state snapshots")
    parser.add_argument("--host", type=loopback_address, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=48_231)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.bind((args.host, args.port))
    print(f"Listening for SpiritValeGameStateBridge on {args.host}:{args.port}", flush=True)
    try:
        while True:
            snapshot = receive_game_state(receiver)
            nearest = nearest_living_monster(snapshot)
            living_count = sum(monster.is_alive and monster.health > 0 for monster in snapshot.monsters)
            position = snapshot.player.position
            nearest_label = nearest.config_id if nearest else "none"
            print(
                f"seq={snapshot.sequence} map={snapshot.map_id or 'unknown'} "
                f"player=({position.x:.1f},{position.y:.1f},{position.z:.1f}) "
                f"monsters={living_count} nearest={nearest_label} "
                f"inventory=equips:{snapshot.inventory.equips},artifacts:{snapshot.inventory.artifacts}",
                flush=True,
            )
    except KeyboardInterrupt:
        pass
    finally:
        receiver.close()


if __name__ == "__main__":
    main()
