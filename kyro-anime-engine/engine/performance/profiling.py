"""Low-overhead context-manager timing profiler."""
from contextlib import contextmanager
from time import perf_counter


class Profiler:
    def __init__(self):
        self.measurements = {}

    @contextmanager
    def measure(self, name):
        started = perf_counter()
        try:
            yield
        finally:
            self.measurements.setdefault(name, []).append(perf_counter() - started)

    def summary(self, name):
        values = self.measurements.get(name, [])
        return {"count": len(values), "total": sum(values),
                "average": sum(values) / len(values) if values else 0.0}
