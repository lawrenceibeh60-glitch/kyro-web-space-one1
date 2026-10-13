"""Keyframe data model for Blender-like animation tracks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Keyframe:
    t: int
    v: float | int | str | bool
    ease: str = "linear"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Keyframe":
        return cls(t=int(payload.get("t", 0)), v=payload.get("v", 0), ease=str(payload.get("ease", "linear")))

    def as_dict(self) -> dict[str, Any]:
        return {"t": self.t, "v": self.v, "ease": self.ease}

