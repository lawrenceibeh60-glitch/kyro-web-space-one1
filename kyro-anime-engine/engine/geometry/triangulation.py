"""Public polygon triangulation interface."""
from engine.math.triangulation import triangulate


def triangulate_polygon(points):
    return triangulate(points)
