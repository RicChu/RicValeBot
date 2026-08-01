from __future__ import annotations

class SkillScheduler:
    def __init__(self, queue_interval_ms: int, schedules: tuple[tuple[str, float], ...]) -> None:
        self.queue_interval=queue_interval_ms/1000; self.schedules=schedules; self.queue=[]; self.next_due=[]; self.last_pop=float("-inf"); self.started=False
    def tick(self, now: float) -> None:
        if not self.started:
            self.queue.extend(key for key,_ in self.schedules); self.next_due=[now+i for _,i in self.schedules]; self.started=True; return
        for i,(key,interval) in enumerate(self.schedules):
            if now>=self.next_due[i]: self.queue.append(key); self.next_due[i]=now+interval
    def pop_ready(self, now: float) -> str | None:
        if self.queue and now-self.last_pop>=self.queue_interval-1e-9:
            self.last_pop=now; return self.queue.pop(0)
        return None
