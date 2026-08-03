from __future__ import annotations

from typing import Any, Callable

import mss


class ReusableMSSCapture:
    """Lazily create one MSS capture object and reuse it across frames."""

    def __init__(self, factory: Callable[[], Any] | None = None) -> None:
        self._factory = factory or mss.MSS
        self._capture: Any | None = None

    def grab(self, monitor: dict[str, int]) -> Any:
        if self._capture is None:
            self._capture = self._factory()
        return self._capture.grab(monitor)

    def close(self) -> None:
        if self._capture is not None and hasattr(self._capture, "close"):
            self._capture.close()
        self._capture = None
