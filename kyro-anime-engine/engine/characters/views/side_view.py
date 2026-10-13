"""Project a front-view character into a depth-compressed side view."""


def side_view(points, depth_scale=0.35):
    if depth_scale <= 0:
        raise ValueError("depth_scale must be positive")
    return {name: (position[1], position[0] * depth_scale)
            for name, position in points.items()}
