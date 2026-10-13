"""Analytic 2D two-bone inverse kinematics solver."""
import math


def solve_two_bone(root, target, length_a, length_b, *, bend=1):
    if length_a <= 0 or length_b <= 0:
        raise ValueError("Bone lengths must be positive")
    dx, dy = target[0] - root[0], target[1] - root[1]
    distance = math.hypot(dx, dy)
    if distance == 0:
        return {"reachable": False, "joint": (root[0] + length_a, root[1]), "end": tuple(root),
                "root_angle": 0.0, "joint_angle": 180.0}
    min_reach, max_reach = abs(length_a - length_b), length_a + length_b
    clamped = max(min_reach + 1e-9, min(max_reach - 1e-9, distance))
    target_angle = math.atan2(dy, dx)
    root_offset = math.acos(max(-1, min(1, (length_a ** 2 + clamped ** 2 - length_b ** 2)
                                            / (2 * length_a * clamped))))
    root_angle = target_angle + (1 if bend >= 0 else -1) * root_offset
    joint = (root[0] + length_a * math.cos(root_angle), root[1] + length_a * math.sin(root_angle))
    actual_end = (root[0] + clamped * math.cos(target_angle), root[1] + clamped * math.sin(target_angle))
    joint_angle = math.pi - math.acos(max(-1, min(1, (length_a ** 2 + length_b ** 2 - clamped ** 2)
                                                     / (2 * length_a * length_b))))
    return {"reachable": min_reach <= distance <= max_reach, "joint": joint, "end": actual_end,
            "root_angle": math.degrees(root_angle), "joint_angle": math.degrees(joint_angle)}
