"""Timeline utilities for Blender-style animation editing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TimelineKeyframe:
    t: int
    value: float
    ease: str = "linear"

    def as_dict(self) -> Dict[str, Any]:
        return {"t": self.t, "v": self.value, "ease": self.ease}


@dataclass
class AnimationTrack:
    channel: str
    keyframes: List[TimelineKeyframe] = field(default_factory=list)

    def set_key(self, time: int, value: float, ease: str = "linear") -> TimelineKeyframe:
        for key in self.keyframes:
            if key.t == time:
                key.value = value
                key.ease = ease
                return key
        item = TimelineKeyframe(time, value, ease)
        self.keyframes.append(item)
        self.keyframes.sort(key=lambda k: k.t)
        return item

    def delete_key(self, time: int) -> bool:
        for idx, key in enumerate(self.keyframes):
            if key.t == time:
                self.keyframes.pop(idx)
                return True
        return False

    def as_dict(self) -> List[Dict[str, Any]]:
        return [key.as_dict() for key in self.keyframes]


@dataclass
class AnimationTimeline:
    fps: int = 12
    duration: int = 24
    tracks: Dict[str, AnimationTrack] = field(default_factory=dict)

    def ensure_track(self, channel: str) -> AnimationTrack:
        track = self.tracks.get(channel)
        if track is None:
            track = AnimationTrack(channel=channel)
            self.tracks[channel] = track
        return track

    def set_key(self, channel: str, time: int, value: float, ease: str = "linear") -> TimelineKeyframe:
        return self.ensure_track(channel).set_key(time, value, ease)

    def delete_key(self, channel: str, time: int) -> bool:
        track = self.tracks.get(channel)
        if not track:
            return False
        return track.delete_key(time)

    def apply_ops(self, ops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for op in ops:
            kind = op.get("op")
            if kind == "set_key":
                key = self.set_key(op["channel"], int(op["time"]), float(op["value"]), op.get("ease", "linear"))
                results.append({"op": "set_key", "channel": op["channel"], "time": key.t, "value": key.value, "ease": key.ease})
            elif kind == "delete_key":
                ok = self.delete_key(op["channel"], int(op["time"]))
                results.append({"op": "delete_key", "channel": op["channel"], "time": int(op["time"]), "ok": ok})
            else:
                raise ValueError(f"Unsupported operation: {kind}")
        return results

    def as_dict(self) -> Dict[str, Any]:
        return {
            "fps": self.fps,
            "duration": self.duration,
            "tracks": {channel: track.as_dict() for channel, track in sorted(self.tracks.items())},
        }

