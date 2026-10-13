"""Simple byte-budget accounting for transient engine resources."""
import threading


class MemoryBudget:
    def __init__(self, limit_bytes):
        if limit_bytes < 0:
            raise ValueError("Memory limit must be non-negative")
        self.limit_bytes = limit_bytes
        self.used_bytes = 0
        self._lock = threading.Lock()

    def reserve(self, amount):
        if amount < 0:
            raise ValueError("Reservation must be non-negative")
        with self._lock:
            if self.used_bytes + amount > self.limit_bytes:
                return False
            self.used_bytes += amount
            return True

    def release(self, amount):
        if amount < 0:
            raise ValueError("Release must be non-negative")
        with self._lock:
            if amount > self.used_bytes:
                raise ValueError("Cannot release more memory than reserved")
            self.used_bytes -= amount
