"""Apply weighted bone translations and rotations to vector points."""
import math


def deform_point(point, influences, bone_transforms):
    if not influences:
        return tuple(point[:2])
    total = sum(max(0.0, weight) for _, weight in influences)
    if total <= 0:
        return tuple(point[:2])
    x_sum = y_sum = 0.0
    for bone_id, weight in influences:
        transform = bone_transforms.get(bone_id)
        if transform is None or weight <= 0:
            continue
        angle = math.radians(transform.get("rotation", 0))
        x, y = point[0], point[1]
        rotated = (x * math.cos(angle) - y * math.sin(angle),
                   x * math.sin(angle) + y * math.cos(angle))
        x_sum += (rotated[0] + transform.get("x", 0)) * weight
        y_sum += (rotated[1] + transform.get("y", 0)) * weight
    return (x_sum / total, y_sum / total)


def deform_points(points, weights, bone_transforms):
    return [deform_point(point, weights.get(index, []), bone_transforms)
            for index, point in enumerate(points)]
