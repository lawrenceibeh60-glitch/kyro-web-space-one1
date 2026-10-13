"""Immutable render output settings and input validation."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RenderSettings:
    width: int
    height: int
    scale: int = 1
    background: str = "#ffffff"
    antialias: int = 1

    def __post_init__(self):
        if min(self.width, self.height, self.scale, self.antialias) < 1:
            raise ValueError("Render dimensions, scale, and antialias factor must be positive")

    @property
    def output_size(self):
        factor = self.scale * self.antialias
        return self.width * factor, self.height * factor
