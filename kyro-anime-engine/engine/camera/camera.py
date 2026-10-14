"""Camera value object with pan, zoom, roll, 3D spatial, and cinematic properties."""
import math
from dataclasses import dataclass, field
from engine.camera.camera_transform import screen_to_world, world_to_screen
from engine.camera.zoom import clamp_zoom


@dataclass
class Camera:
    # 2D properties (existing, backward-compatible)
    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0
    rotation: float = 0.0

    # 3D spatial extension
    z: float = 0.0
    rotation_x: float = 0.0  # pitch (degrees)
    rotation_y: float = 0.0  # yaw (degrees)

    # Cinematic lens properties
    fov: float = 60.0  # vertical field of view in degrees
    focal_length: float = 50.0  # mm equivalent
    sensor_width: float = 36.0  # mm
    near_clip: float = 0.1
    far_clip: float = 10000.0
    focus_distance: float = 100.0
    aperture: float = 0.0  # 0 = no DOF blur

    # Quaternion orientation cache (w, x, y, z) — computed on demand
    _orientation: tuple | None = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        self.zoom = clamp_zoom(self.zoom)
        self.fov = max(1.0, min(179.0, self.fov))
        self.near_clip = max(0.001, self.near_clip)
        if self.far_clip <= self.near_clip:
            self.far_clip = self.near_clip + 1.0

    def pan(self, dx, dy):
        self.x += dx
        self.y += dy
        return self

    def dolly(self, dz):
        """Move camera along its local Z axis (physical movement, not zoom)."""
        self.z += dz
        return self

    def set_zoom(self, zoom):
        self.zoom = clamp_zoom(zoom)
        return self

    def set_fov(self, fov_degrees):
        """Optical zoom via FOV change (distinct from physical dolly)."""
        self.fov = max(1.0, min(179.0, fov_degrees))
        self._orientation = None
        return self

    def orbit(self, target, angle_y_degrees, angle_x_degrees=0):
        """Orbit camera around a target point (x, y, z)."""
        from engine.math.quaternions import from_axis_angle, multiply as qmul, normalize
        dx = self.x - target[0]
        dy = self.y - target[1]
        dz = self.z - (target[2] if len(target) > 2 else 0)
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dist < 1e-9:
            return self
        ay = math.radians(angle_y_degrees)
        ax = math.radians(angle_x_degrees)
        cos_a, sin_a = math.cos(ay), math.sin(ay)
        nx = dx * cos_a - dz * sin_a
        nz = dx * sin_a + dz * cos_a
        self.x = target[0] + nx
        self.z = (target[2] if len(target) > 2 else 0) + nz
        self.rotation_y += angle_y_degrees
        self.rotation_x += angle_x_degrees
        self._orientation = None
        return self

    @property
    def orientation_quaternion(self):
        """Compute quaternion from Euler angles (YXZ order to avoid gimbal issues)."""
        if self._orientation is not None:
            return self._orientation
        from engine.math.quaternions import from_axis_angle, multiply as qmul, normalize
        rx = math.radians(self.rotation_x)
        ry = math.radians(self.rotation_y)
        rz = math.radians(self.rotation)
        qx = from_axis_angle((1, 0, 0), rx)
        qy = from_axis_angle((0, 1, 0), ry)
        qz = from_axis_angle((0, 0, 1), rz)
        self._orientation = normalize(qmul(qy, qmul(qx, qz)))
        return self._orientation

    def to_dict(self):
        result = {"x": self.x, "y": self.y, "zoom": self.zoom, "rotation": self.rotation}
        if self.z != 0:
            result["z"] = self.z
        if self.rotation_x != 0:
            result["rotation_x"] = self.rotation_x
        if self.rotation_y != 0:
            result["rotation_y"] = self.rotation_y
        if self.fov != 60.0:
            result["fov"] = self.fov
        if self.near_clip != 0.1:
            result["near_clip"] = self.near_clip
        if self.far_clip != 10000.0:
            result["far_clip"] = self.far_clip
        if self.focus_distance != 100.0:
            result["focus_distance"] = self.focus_distance
        if self.aperture != 0:
            result["aperture"] = self.aperture
        return result

    @classmethod
    def from_dict(cls, data):
        if not data:
            return cls()
        return cls(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            zoom=data.get("zoom", data.get("scale_x", 1.0)),
            rotation=data.get("rotation", 0.0),
            z=data.get("z", 0.0),
            rotation_x=data.get("rotation_x", 0.0),
            rotation_y=data.get("rotation_y", 0.0),
            fov=data.get("fov", 60.0),
            near_clip=data.get("near_clip", 0.1),
            far_clip=data.get("far_clip", 10000.0),
            focus_distance=data.get("focus_distance", 100.0),
            aperture=data.get("aperture", 0.0),
        )

    def world_to_screen(self, point, viewport=(0, 0)):
        return world_to_screen(point, self.to_dict(), viewport=viewport)

    def screen_to_world(self, point, viewport=(0, 0)):
        return screen_to_world(point, self.to_dict(), viewport=viewport)
