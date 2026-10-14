"""Camera transform evaluation and world/screen coordinate conversion.

Supports both 2D orthographic (default, backward-compatible) and 3D perspective modes.
"""
import math


def world_to_screen(point, camera, *, viewport=(0, 0)):
    """Convert world-space point to screen coordinates (2D orthographic)."""
    x, y = point[0] - camera.get("x", 0), point[1] - camera.get("y", 0)
    zoom_x = camera.get("scale_x", camera.get("zoom", 1))
    zoom_y = camera.get("scale_y", camera.get("zoom", 1))
    angle = math.radians(camera.get("rotation", 0))
    cosine, sine = math.cos(angle), math.sin(angle)
    return (
        viewport[0] + (x * cosine - y * sine) * zoom_x,
        viewport[1] + (x * sine + y * cosine) * zoom_y,
    )


def screen_to_world(point, camera, *, viewport=(0, 0)):
    """Convert screen coordinates to world-space point (2D orthographic)."""
    zoom_x = camera.get("scale_x", camera.get("zoom", 1))
    zoom_y = camera.get("scale_y", camera.get("zoom", 1))
    if zoom_x == 0 or zoom_y == 0:
        raise ValueError("Camera zoom must be non-zero")
    x, y = (point[0] - viewport[0]) / zoom_x, (point[1] - viewport[1]) / zoom_y
    angle = math.radians(-camera.get("rotation", 0))
    cosine, sine = math.cos(angle), math.sin(angle)
    return (x * cosine - y * sine + camera.get("x", 0),
            x * sine + y * cosine + camera.get("y", 0))


def project_perspective(point_3d, camera, *, viewport_size=(1280, 720)):
    """Project a 3D world point to 2D screen using perspective projection.

    Args:
        point_3d: (x, y, z) world-space coordinates.
        camera: dict with camera parameters (x, y, z, rotation_x, rotation_y,
                rotation, fov, near_clip, far_clip).
        viewport_size: (width, height) in pixels.

    Returns:
        (screen_x, screen_y, depth) tuple. Points behind the camera return None.
    """
    cx = camera.get("x", 0)
    cy = camera.get("y", 0)
    cz = camera.get("z", 0)

    # Translate to camera space
    dx = point_3d[0] - cx
    dy = point_3d[1] - cy
    dz = (point_3d[2] if len(point_3d) > 2 else 0) - cz

    # Rotate by camera orientation (YXZ Euler order)
    ry = math.radians(camera.get("rotation_y", 0))
    rx = math.radians(camera.get("rotation_x", 0))
    rz = math.radians(camera.get("rotation", 0))

    # Yaw
    cos_y, sin_y = math.cos(ry), math.sin(ry)
    dx, dz = dx * cos_y + dz * sin_y, -dx * sin_y + dz * cos_y

    # Pitch
    cos_x, sin_x = math.cos(rx), math.sin(rx)
    dy, dz = dy * cos_x - dz * sin_x, dy * sin_x + dz * cos_x

    # Roll
    cos_z, sin_z = math.cos(rz), math.sin(rz)
    dx, dy = dx * cos_z - dy * sin_z, dx * sin_z + dy * cos_z

    near = camera.get("near_clip", 0.1)
    far = camera.get("far_clip", 10000.0)

    # Behind camera or outside clip
    if dz >= -near or dz <= -far:
        return None

    # Perspective divide
    fov_rad = math.radians(camera.get("fov", 60.0))
    f = 1.0 / math.tan(fov_rad / 2.0)
    width, height = viewport_size
    aspect = width / height if height > 0 else 1.0

    screen_x = (dx * f / (aspect * -dz)) * (width / 2) + (width / 2)
    screen_y = (dy * f / -dz) * (height / 2) + (height / 2)

    return (screen_x, screen_y, -dz)


def interpolate_camera(cam_a, cam_b, t):
    """Smoothly interpolate between two camera states.

    Uses linear interpolation for position/FOV and quaternion slerp for
    orientation to prevent sudden flips or gimbal lock.

    Args:
        cam_a: dict or Camera, start state.
        cam_b: dict or Camera, end state.
        t: float 0..1 interpolation factor.

    Returns:
        dict with interpolated camera parameters.
    """
    a = cam_a.to_dict() if hasattr(cam_a, "to_dict") else (cam_a or {})
    b = cam_b.to_dict() if hasattr(cam_b, "to_dict") else (cam_b or {})

    def lerp_val(key, default=0.0):
        va = a.get(key, default)
        vb = b.get(key, default)
        return va + (vb - va) * t

    result = {
        "x": lerp_val("x"),
        "y": lerp_val("y"),
        "z": lerp_val("z"),
        "zoom": lerp_val("zoom", 1.0),
        "fov": lerp_val("fov", 60.0),
        "focus_distance": lerp_val("focus_distance", 100.0),
        "aperture": lerp_val("aperture"),
        "near_clip": lerp_val("near_clip", 0.1),
        "far_clip": lerp_val("far_clip", 10000.0),
    }

    # Use quaternion slerp for rotation to avoid gimbal lock and flips
    has_3d_rotation = any(k in a or k in b for k in ("rotation_x", "rotation_y"))
    if has_3d_rotation:
        from engine.math.quaternions import from_axis_angle, multiply as qmul, slerp, normalize

        def quat_from_euler(euler_dict):
            rx = math.radians(euler_dict.get("rotation_x", 0))
            ry = math.radians(euler_dict.get("rotation_y", 0))
            rz = math.radians(euler_dict.get("rotation", 0))
            qx = from_axis_angle((1, 0, 0), rx)
            qy = from_axis_angle((0, 1, 0), ry)
            qz = from_axis_angle((0, 0, 1), rz)
            return normalize(qmul(qy, qmul(qx, qz)))

        qa = quat_from_euler(a)
        qb = quat_from_euler(b)
        qi = slerp(qa, qb, t)

        # Extract Euler angles back (YXZ convention)
        sinr_cosp = 2 * (qi[0] * qi[1] + qi[2] * qi[3])
        cosr_cosp = 1 - 2 * (qi[1] * qi[1] + qi[2] * qi[2])
        result["rotation_x"] = math.degrees(math.atan2(sinr_cosp, cosr_cosp))

        sinp = 2 * (qi[0] * qi[2] - qi[3] * qi[1])
        sinp = max(-1.0, min(1.0, sinp))
        result["rotation_y"] = math.degrees(math.asin(sinp))

        siny_cosp = 2 * (qi[0] * qi[3] + qi[1] * qi[2])
        cosy_cosp = 1 - 2 * (qi[2] * qi[2] + qi[3] * qi[3])
        result["rotation"] = math.degrees(math.atan2(siny_cosp, cosy_cosp))
    else:
        # Simple 2D rotation lerp with shortest-path
        ra = a.get("rotation", 0)
        rb = b.get("rotation", 0)
        diff = (rb - ra) % 360
        if diff > 180:
            diff -= 360
        result["rotation"] = ra + diff * t
        result["rotation_x"] = 0
        result["rotation_y"] = 0

    return result
