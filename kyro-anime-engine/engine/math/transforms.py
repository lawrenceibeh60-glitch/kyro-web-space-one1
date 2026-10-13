"""Composable 2D transforms and point conversion."""
import math
from engine.math.matrices import multiply, rotation, scaling, transform_point, translation


def compose(*, x=0, y=0, rotation_degrees=0, scale_x=1, scale_y=1, origin=(0, 0)):
    ox, oy = origin
    to_origin = translation(-ox, -oy)
    from_origin = translation(ox + x, oy + y)
    return multiply(from_origin, multiply(
        rotation(math.radians(rotation_degrees)),
        multiply(scaling(scale_x, scale_y), to_origin),
    ))


def apply(transform, point):
    return transform_point(transform, point)
