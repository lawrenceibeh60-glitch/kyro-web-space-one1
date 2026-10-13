"""2D affine matrices stored as row-major 3x3 tuples."""
import math

IDENTITY = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))


def multiply(a, b):
    return tuple(tuple(sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)) for r in range(3))


def translation(x, y):
    return ((1.0, 0.0, x), (0.0, 1.0, y), (0.0, 0.0, 1.0))


def scaling(x, y=None):
    y = x if y is None else y
    return ((x, 0.0, 0.0), (0.0, y, 0.0), (0.0, 0.0, 1.0))


def rotation(radians):
    c, s = math.cos(radians), math.sin(radians)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def transform_point(matrix, point):
    x, y = point
    w = matrix[2][0] * x + matrix[2][1] * y + matrix[2][2]
    if w == 0:
        raise ValueError("Point transformed to zero homogeneous coordinate")
    return (
        (matrix[0][0] * x + matrix[0][1] * y + matrix[0][2]) / w,
        (matrix[1][0] * x + matrix[1][1] * y + matrix[1][2]) / w,
    )


def inverse(matrix):
    a, b, tx = matrix[0]
    c, d, ty = matrix[1]
    determinant = a * d - b * c
    if abs(determinant) < 1e-12:
        raise ValueError("Cannot invert a singular affine matrix")
    inv = 1 / determinant
    return ((d * inv, -b * inv, (b * ty - d * tx) * inv),
            (-c * inv, a * inv, (c * tx - a * ty) * inv),
            (0.0, 0.0, 1.0))
