"""Front view placement using bilateral symmetry."""


def front_view(points):
    return {name: tuple(position) for name, position in points.items()}
