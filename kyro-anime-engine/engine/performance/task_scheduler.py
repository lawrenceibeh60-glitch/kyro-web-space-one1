"""Small deterministic priority task scheduler."""
import heapq
import itertools


class TaskScheduler:
    def __init__(self):
        self._queue = []
        self._sequence = itertools.count()

    def submit(self, callback, *, priority=0):
        handle = next(self._sequence)
        heapq.heappush(self._queue, (priority, handle, callback))
        return handle

    def run_next(self):
        if not self._queue:
            return False
        _, _, callback = heapq.heappop(self._queue)
        callback()
        return True

    def run_all(self):
        while self.run_next():
            pass
