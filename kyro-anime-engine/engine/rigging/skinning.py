"""Linear blend skinning over per-vertex bone influences."""
from engine.rigging.deformation import deform_point


def normalize_weights(influences):
    valid = [(bone_id, max(0.0, float(weight))) for bone_id, weight in influences if weight > 0]
    total = sum(weight for _, weight in valid)
    return [] if total == 0 else [(bone_id, weight / total) for bone_id, weight in valid]


def skin_vertices(vertices, weights, bone_transforms):
    result = []
    for index, vertex in enumerate(vertices):
        influences = normalize_weights(weights.get(index, []))
        result.append(deform_point(vertex, influences, bone_transforms))
    return result
