"""Create filled polygon commands."""
from engine.rendering.draw_command import DrawCommand


def render_fill(points, *, color, opacity=1, z=0):
    points = [tuple(point[:2]) for point in points]
    if len(points) < 3:
        return None
    return DrawCommand("polygon", points, color=color, fill=color,
                       opacity=max(0, min(1, opacity)), z=z)
