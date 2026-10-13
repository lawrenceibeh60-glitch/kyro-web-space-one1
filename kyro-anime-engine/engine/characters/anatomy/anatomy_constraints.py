"""Constraint checks for generated anatomy."""


def validate_joints(joints, required=()):
    missing = [name for name in required if name not in joints]
    if missing:
        return [f"Missing joint: {name}" for name in missing]
    issues = []
    for name, point in joints.items():
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            issues.append(f"Joint {name} must have a 2D position")
    return issues


def clamp_angle(angle, minimum=-180, maximum=180):
    if minimum > maximum:
        raise ValueError("minimum must not exceed maximum")
    return max(minimum, min(maximum, angle))
