"""Two-segment leg kinematics."""
from engine.characters.anatomy.arms import arm_joints


def leg_joints(hip, thigh_length, shin_length, angle, knee_angle):
    return arm_joints(hip, thigh_length, shin_length, angle, knee_angle) | {"hip": tuple(hip)}
