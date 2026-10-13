"""Convert polygon contours to indexed triangle meshes."""
from engine.geometry.mesh2d import Mesh2D
from engine.math.triangulation import triangulate


def tessellate_polygon(points):
    vertices = [tuple(point[:2]) for point in points]
    return Mesh2D(vertices, triangulate(vertices))
