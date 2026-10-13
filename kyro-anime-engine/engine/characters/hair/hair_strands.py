"""Interpolate smooth strand points through control points."""


def interpolate_strand(points, samples_per_segment=4):
    if samples_per_segment < 1:
        raise ValueError("samples_per_segment must be positive")
    if len(points) < 2:
        return list(points)
    result = []
    for start, end in zip(points, points[1:]):
        for step in range(samples_per_segment):
            t = step / samples_per_segment
            result.append(tuple(a + (b - a) * t for a, b in zip(start, end)))
    result.append(tuple(points[-1]))
    return result
