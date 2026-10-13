"""Stateful render job progress and cancellation."""
from dataclasses import dataclass, field


@dataclass
class RenderJob:
    frames: list
    status: str = "pending"
    completed_frames: list = field(default_factory=list)
    error: str = ""

    @property
    def progress(self):
        return len(self.completed_frames) / len(self.frames) if self.frames else 1.0

    def start(self):
        if self.status != "pending":
            raise RuntimeError("Only pending jobs can start")
        self.status = "running"

    def complete_frame(self, frame):
        if self.status != "running" or frame not in self.frames:
            raise RuntimeError("Frame is not part of a running job")
        if frame not in self.completed_frames:
            self.completed_frames.append(frame)
        if len(self.completed_frames) == len(self.frames):
            self.status = "completed"

    def fail(self, error):
        self.error, self.status = str(error), "failed"

    def cancel(self):
        if self.status in ("pending", "running"):
            self.status = "cancelled"
