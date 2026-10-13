"""Back view projection, preserving named landmarks."""


def back_view(points, center_x=0):
    return {name: (2 * center_x - position[0], position[1])
            for name, position in points.items()}
