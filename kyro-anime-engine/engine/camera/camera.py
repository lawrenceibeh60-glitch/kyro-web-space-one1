"""Camera value object with pan, zoom, roll, and coordinate transforms."""
from dataclasses import dataclass
from engine.camera.camera_transform import screen_to_world, world_to_screen
from engine.camera.zoom import clamp_zoom


@dataclass
class Camera:
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    rotation: float = 0.0

    def __post_init__(self):
        self.zoom = clamp_zoom(self.zoom)

    def pan(self, dx, dy):
        self.x += dx
        self.y += dy
        return self

    def set_zoom(self, zoom):
        self.zoom = clamp_zoom(zoom)
        return self

    def to_dict(self):
        return {"x": self.x, "y": self.y, "zoom": self.zoom, "rotation": self.rotation}

    def world_to_screen(self, point, viewport=(0, 0)):
        return world_to_screen(point, self.to_dict(), viewport=viewport)

    def screen_to_world(self, point, viewport=(0, 0)):
        return screen_to_world(point, self.to_dict(), viewport=viewport)
