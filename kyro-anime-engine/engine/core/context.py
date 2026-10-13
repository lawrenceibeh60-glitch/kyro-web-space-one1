"""Per-evaluation context passed through engine stages."""
from dataclasses import dataclass, field
from engine.core.diagnostics import DiagnosticBag
from engine.core.event_bus import EventBus
from engine.core.registry import Registry


@dataclass
class EngineContext:
    project: dict | None = None
    frame: int = 0
    fps: float = 12.0
    events: EventBus = field(default_factory=EventBus)
    services: Registry = field(default_factory=Registry)
    diagnostics: DiagnosticBag = field(default_factory=DiagnosticBag)
    cancelled: bool = False

    @property
    def time_seconds(self):
        return self.frame / self.fps if self.fps > 0 else 0.0

    def cancel(self):
        self.cancelled = True
        self.events.emit("engine:cancelled", self)
