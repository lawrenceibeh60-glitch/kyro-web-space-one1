"""Material properties for cel-shaded vector objects."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    color: str = "#ffffff"
    roughness: float = 1.0
    emission: float = 0.0
    opacity: float = 1.0
    receives_light: bool = True

    def __post_init__(self):
        if not 0 <= self.roughness <= 1 or not 0 <= self.opacity <= 1 or self.emission < 0:
            raise ValueError("Material roughness/opacity must be 0..1 and emission non-negative")

    def to_dict(self):
        return {
            "color": self.color, "roughness": self.roughness,
            "emission": self.emission, "opacity": self.opacity,
            "receives_light": self.receives_light,
        }
