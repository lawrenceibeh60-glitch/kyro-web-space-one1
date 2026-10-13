"""Create vector draw commands for stroked paths."""
from engine.rendering.draw_command import DrawCommand


def render_line(points, *, color="#111111", width=1, opacity=1, z=0):
    points = [tuple(point[:2]) for point in points]
    if len(points) < 2 or width <= 0:
        return None
    return DrawCommand("line", points, color=color, width=width,
                       opacity=max(0, min(1, opacity)), z=z)
