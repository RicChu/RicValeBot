from __future__ import annotations


class MapArrivalWaitController:
    """Blocks route input until the active map's arrival minimap is visible."""

    def __init__(self) -> None:
        self.state = "idle"
        self._route_start_at = 0.0

    @property
    def active(self) -> bool:
        return self.state in {"waiting_for_arrival", "waiting_before_route"}

    def start(self) -> None:
        self.state = "waiting_for_arrival"
        self._route_start_at = 0.0

    def cancel(self) -> None:
        self.state = "idle"
        self._route_start_at = 0.0

    def observe(self, arrival_visible: bool, now: float = 0.0, route_start_delay_seconds: float = 0.0) -> bool:
        if self.active and arrival_visible:
            if self.state == "waiting_for_arrival" and route_start_delay_seconds > 0:
                self.state = "waiting_before_route"
                self._route_start_at = now + route_start_delay_seconds
            elif self.state == "waiting_for_arrival":
                self.state = "arrived"
        if self.state == "waiting_before_route" and now >= self._route_start_at:
            self.state = "arrived"
        return self.active
