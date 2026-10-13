"""Polyline smoothing that preserves endpoints and optional pressure."""
def moving_average(points, radius=2):
    points = [tuple(point) for point in points]
    if radius < 1 or len(points) < 3:
        return points
    result = [points[0]]
    for index in range(1, len(points) - 1):
        start, end = max(0, index - radius), min(len(points), index + radius + 1)
        result.append(tuple(sum(point[axis] for point in points[start:end]) / (end - start)
                            for axis in range(len(points[index]))))
    result.append(points[-1])
    return result


def chaikin(points, *, iterations=1, closed=False):
    result = [tuple(point) for point in points]
    for _ in range(max(0, iterations)):
        if len(result) < 2:
            break
        refined = []
        pairs = list(zip(result, result[1:]))
        if closed:
            pairs.append((result[-1], result[0]))
        else:
            refined.append(result[0])
        for a, b in pairs:
            refined.extend((
                tuple(0.75 * x + 0.25 * y for x, y in zip(a, b)),
                tuple(0.25 * x + 0.75 * y for x, y in zip(a, b)),
            ))
        if not closed:
            refined.append(result[-1])
        result = refined
    return result
