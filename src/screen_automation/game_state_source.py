"""Threaded loopback UDP source for the latest valid game-state snapshot."""

from __future__ import annotations

import socket
import threading
import time
from collections.abc import Callable

from .game_state import GameStateSnapshot, decode_game_state


class GameStateSource:
    def __init__(
        self,
        host: str,
        port: int,
        stale_after_ms: int,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._host = host
        self._port = port
        self._stale_after_seconds = stale_after_ms / 1000.0
        self._clock = clock
        self._lock = threading.Lock()
        self._snapshot: GameStateSnapshot | None = None
        self._received_at: float | None = None
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def address(self) -> tuple[str, int]:
        sock = self._socket
        if sock is None:
            raise RuntimeError("game-state source is not running")
        host, port = sock.getsockname()
        return str(host), int(port)

    def start(self) -> None:
        if self._socket is not None:
            return
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            receiver.bind((self._host, self._port))
            receiver.settimeout(0.1)
        except BaseException:
            receiver.close()
            raise
        self._stop_event.clear()
        self._socket = receiver
        self._thread = threading.Thread(target=self._receive_loop, name="game-state-source", daemon=True)
        self._thread.start()

    def latest(self) -> GameStateSnapshot | None:
        now = self._clock()
        with self._lock:
            if self._received_at is None or now - self._received_at > self._stale_after_seconds:
                return None
            return self._snapshot

    def stop(self) -> None:
        receiver = self._socket
        thread = self._thread
        self._socket = None
        self._thread = None
        self._stop_event.set()
        if receiver is not None:
            receiver.close()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=0.5)

    def _receive_loop(self) -> None:
        receiver = self._socket
        if receiver is None:
            return
        while not self._stop_event.is_set():
            try:
                payload, _source = receiver.recvfrom(65_535)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                snapshot = decode_game_state(payload)
            except (KeyError, TypeError, UnicodeDecodeError, ValueError):
                continue
            received_at = self._clock()
            with self._lock:
                self._snapshot = snapshot
                self._received_at = received_at
