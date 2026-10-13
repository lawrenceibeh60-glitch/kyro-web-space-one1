"""Track helpers for ordered keyframes."""
from __future__ import annotations

from dataclasses import dataclass, field

from engine.animation.keyframe import Keyframe


@dataclass(slots=True)
class KeyframeTrack:
    channel: str
    keyframes: list[Keyframe] = field(default_factory=list)

    def add(self, t: int, value, ease: str = "linear") -> Keyframe:
        for k in self.keyframes:
            if k.t == t:
                k.v = value
                k.ease = ease
                return k
        key = Keyframe(t=t, v=value, ease=ease)
        self.keyframes.append(key)
        self.keyframes.sort(key=lambda item: item.t)
        return key

    def remove(self, t: int) -> Keyframe | None:
        for i, k in enumerate(self.keyframes):
            if k.t == t:
                return self.keyframes.pop(i)
        return None

    def move(self, old_t: int, new_t: int) -> Keyframe | None:
        key = self.remove(old_t)
        if key is None:
            return None
        key.t = new_t
        self.keyframes.append(key)
        self.keyframes.sort(key=lambda item: item.t)
        return key

    def as_dict(self) -> list[dict]:
        return [k.as_dict() for k in self.keyframes]

