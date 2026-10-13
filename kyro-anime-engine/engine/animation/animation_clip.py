"""Animation clip range and playback-time utilities."""
from dataclasses import dataclass


@dataclass(frozen=True)
class AnimationClip:
    id: str
    start: int = 0
    end: int = 24
    loop: bool = False
    name: str = ""

    def __post_init__(self):
        if not self.id or self.start < 0 or self.end <= self.start:
            raise ValueError("Clip requires an id and a non-empty non-negative frame range")

    @property
    def duration(self):
        return self.end - self.start

    def frame_at(self, local_frame):
        if self.loop:
            return self.start + local_frame % self.duration
        return min(self.end - 1, max(self.start, self.start + local_frame))

    @classmethod
    def from_dict(cls, payload):
        return cls(
            id=payload["id"], start=payload.get("start", 0),
            end=payload.get("end", 24), loop=payload.get("loop", False),
            name=payload.get("name", ""),
        )
