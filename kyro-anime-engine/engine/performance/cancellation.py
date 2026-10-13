"""Cooperative cancellation token."""
import threading


class CancellationToken:
    def __init__(self):
        self._event = threading.Event()

    @property
    def cancelled(self):
        return self._event.is_set()

    def cancel(self):
        self._event.set()

    def raise_if_cancelled(self):
        if self.cancelled:
            raise InterruptedError("Operation was cancelled")
