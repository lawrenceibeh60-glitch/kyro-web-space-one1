"""Audio clip and timeline track primitives."""
from dataclasses import dataclass, field


@dataclass
class AudioTrack:
    id: str
    clips: list = field(default_factory=list)
    gain: float = 1.0
    muted: bool = False

    def add_clip(self, clip):
        start, duration = float(clip["start"]), float(clip["duration"])
        if start < 0 or duration < 0:
            raise ValueError("Clip start and duration must be non-negative")
        normalized = {**clip, "start": start, "duration": duration}
        self.clips.append(normalized)
        self.clips.sort(key=lambda item: item["start"])
        return normalized

    def remove_clip(self, clip_id):
        before = len(self.clips)
        self.clips[:] = [clip for clip in self.clips if clip.get("id") != clip_id]
        return len(self.clips) != before

    @property
    def duration(self):
        return max((clip["start"] + clip["duration"] for clip in self.clips), default=0)
