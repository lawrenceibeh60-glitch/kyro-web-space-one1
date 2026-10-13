"""Catmull-Rom spline interpolation through supplied control points."""


def catmull_rom(p0, p1, p2, p3, t, *, alpha=0.5):
    t2, t3 = t * t, t * t * t
    return tuple(
        0.5 * ((2 * p1[i]) + (-p0[i] + p2[i]) * t
               + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t2
               + (-p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]) * t3)
        for i in range(len(p1))
    )


def sample(points, segments_per_span=12, *, closed=False):
    points = list(points)
    if len(points) < 2:
        return points
    if segments_per_span < 1:
        raise ValueError("segments_per_span must be at least 1")
    result = []
    spans = len(points) if closed else len(points) - 1
    for span in range(spans):
        p1, p2 = points[span % len(points)], points[(span + 1) % len(points)]
        p0 = points[(span - 1) % len(points)] if closed or span else p1
        p3 = points[(span + 2) % len(points)] if closed or span + 2 < len(points) else p2
        for index in range(segments_per_span):
            result.append(catmull_rom(p0, p1, p2, p3, index / segments_per_span))
    if not closed:
        result.append(tuple(points[-1]))
    return result
