"""Collect render command counts and elapsed time metadata."""
from dataclasses import dataclass, field
from time import perf_counter


@dataclass
class RenderDiagnostics:
    started_at: float = field(default_factory=perf_counter)
    command_count: int = 0
    warnings: list = field(default_factory=list)
    counters: dict = field(default_factory=dict)

    def count(self, name, amount=1):
        self.counters[name] = self.counters.get(name, 0) + amount

    @property
    def elapsed_seconds(self):
        return max(0.0, perf_counter() - self.started_at)

    def to_dict(self):
        return {"command_count": self.command_count, "warnings": list(self.warnings),
                "counters": dict(self.counters), "elapsed_seconds": self.elapsed_seconds}
