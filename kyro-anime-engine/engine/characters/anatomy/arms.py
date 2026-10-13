"""Two-segment arm kinematics."""
import math


def arm_joints(shoulder, upper_length, lower_length, angle, elbow_angle):
    if upper_length < 0 or lower_length < 0:
        raise ValueError("Limb lengths must be non-negative")
    a, b = math.radians(angle), math.radians(angle + elbow_angle)
    elbow = (shoulder[0] + upper_length * math.cos(a), shoulder[1] + upper_length * math.sin(a))
    wrist = (elbow[0] + lower_length * math.cos(b), elbow[1] + lower_length * math.sin(b))
    return {"shoulder": tuple(shoulder), "elbow": elbow, "wrist": wrist}
