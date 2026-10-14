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


# --- 4x4 matrix operations for 3D spatial transforms ---

IDENTITY_4X4 = tuple(
    tuple(1.0 if r == c else 0.0 for c in range(4)) for r in range(4)
)


def multiply_4x4(a, b):
    """Multiply two 4x4 row-major matrices."""
    return tuple(
        tuple(sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4))
        for r in range(4)
    )


def translation_3d(x, y, z=0.0):
    """4x4 translation matrix."""
    return (
        (1.0, 0.0, 0.0, x),
        (0.0, 1.0, 0.0, y),
        (0.0, 0.0, 1.0, z),
        (0.0, 0.0, 0.0, 1.0),
    )


def scaling_3d(x, y=None, z=None):
    """4x4 scaling matrix. Uniform if only x provided."""
    y = x if y is None else y
    z = x if z is None else z
    return (
        (x, 0.0, 0.0, 0.0),
        (0.0, y, 0.0, 0.0),
        (0.0, 0.0, z, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def rotation_x(radians):
    """4x4 rotation around X axis."""
    c, s = math.cos(radians), math.sin(radians)
    return (
        (1.0, 0.0, 0.0, 0.0),
        (0.0, c, -s, 0.0),
        (0.0, s, c, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def rotation_y(radians):
    """4x4 rotation around Y axis."""
    c, s = math.cos(radians), math.sin(radians)
    return (
        (c, 0.0, s, 0.0),
        (0.0, 1.0, 0.0, 0.0),
        (-s, 0.0, c, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def rotation_z(radians):
    """4x4 rotation around Z axis (equivalent to 2D rotation)."""
    c, s = math.cos(radians), math.sin(radians)
    return (
        (c, -s, 0.0, 0.0),
        (s, c, 0.0, 0.0),
        (0.0, 0.0, 1.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    )


def transform_point_3d(matrix, point):
    """Transform a 3D point by a 4x4 matrix, returning (x, y, z)."""
    x, y, z = point[0], point[1], point[2] if len(point) > 2 else 0.0
    w = sum(matrix[3][i] * p for i, p in enumerate((x, y, z, 1.0)))
    if abs(w) < 1e-12:
        raise ValueError("Point transformed to zero homogeneous coordinate")
    return tuple(
        sum(matrix[r][i] * p for i, p in enumerate((x, y, z, 1.0))) / w
        for r in range(3)
    )


def perspective_projection(fov_y_radians, aspect, near, far):
    """Standard perspective projection matrix.

    Maps view-space coordinates to clip space. fov_y_radians is the vertical
    field of view. aspect is width/height.
    """
    if near <= 0 or far <= near:
        raise ValueError("Invalid clip planes: need 0 < near < far")
    f = 1.0 / math.tan(fov_y_radians / 2.0)
    nf = 1.0 / (near - far)
    return (
        (f / aspect, 0.0, 0.0, 0.0),
        (0.0, f, 0.0, 0.0),
        (0.0, 0.0, (far + near) * nf, 2.0 * far * near * nf),
        (0.0, 0.0, -1.0, 0.0),
    )


def orthographic_projection(left, right, bottom, top, near, far):
    """Orthographic projection matrix."""
    rl = 1.0 / (right - left)
    tb = 1.0 / (top - bottom)
    fn = 1.0 / (far - near)
    return (
        (2.0 * rl, 0.0, 0.0, -(right + left) * rl),
        (0.0, 2.0 * tb, 0.0, -(top + bottom) * tb),
        (0.0, 0.0, -2.0 * fn, -(far + near) * fn),
        (0.0, 0.0, 0.0, 1.0),
    )
