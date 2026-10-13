"""Three-quarter view projection."""


def three_quarter_view(points, depth_scale=0.7, facing=1):
    if depth_scale <= 0 or facing not in (-1, 1):
        raise ValueError("Invalid view projection")
    return {name: (position[0] * depth_scale * facing + position[1] * (1 - depth_scale),
                   position[1])
            for name, position in points.items()}
