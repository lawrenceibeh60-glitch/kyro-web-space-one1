"""Validated KAE output and timing settings."""
from dataclasses import dataclass
import re
from engine.core.errors import ValidationError


@dataclass(frozen=True)
class ProjectSettings:
    width: int = 1280
    height: int = 720
    fps: float = 12
    duration_frames: int = 24
    background: str = "#ffffff"

    def __post_init__(self):
        if isinstance(self.width, bool) or not isinstance(self.width, int) or not 16 <= self.width <= 8192:
            raise ValidationError("width must be an integer in 16..8192")
        if isinstance(self.height, bool) or not isinstance(self.height, int) or not 16 <= self.height <= 8192:
            raise ValidationError("height must be an integer in 16..8192")
        if isinstance(self.fps, bool) or not isinstance(self.fps, (int, float)) or not 0 < self.fps <= 120:
            raise ValidationError("fps must be in (0, 120]")
        if isinstance(self.duration_frames, bool) or not isinstance(self.duration_frames, int) or self.duration_frames < 1:
            raise ValidationError("duration_frames must be a positive integer")
        if not isinstance(self.background, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", self.background):
            raise ValidationError("background must be a #RRGGBB color")

    @classmethod
    def from_dict(cls, data):
        return cls(**{key: value for key, value in data.items() if key in cls.__dataclass_fields__})

    def to_dict(self):
        return {
            "width": self.width, "height": self.height, "fps": self.fps,
            "duration_frames": self.duration_frames, "background": self.background,
        }
