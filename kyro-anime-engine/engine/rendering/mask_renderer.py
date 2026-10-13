"""Binary mask operations on flat coverage buffers."""


def raster_mask(width, height, polygons, *, inside=1.0, outside=0.0):
    from engine.math.polygons import contains
    return [
        inside if any(contains(poly, (x + 0.5, y + 0.5)) for poly in polygons) else outside
        for y in range(height) for x in range(width)
    ]
