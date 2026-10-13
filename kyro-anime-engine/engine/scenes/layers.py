"""Timeline exposure and layer ordering helpers."""


def ordered_layers(layers, *, reverse=False):
    indexed = enumerate(layers)
    return [layer for _, layer in sorted(indexed, key=lambda item: (item[1].get("order", item[0]), item[0]), reverse=reverse)]


def drawing_at_frame(layer, frame):
    for exposure in layer.get("exposures", []):
        start = exposure.get("start", 0)
        length = exposure.get("length", 1)
        if start <= frame < start + length:
            return exposure.get("drawing")
    return None


def visible_layers(scene, frame):
    return [
        layer for layer in scene.get("layers", [])
        if layer.get("visible", True) and drawing_at_frame(layer, frame) is not None
    ]


def exposure_end(exposure):
    return exposure.get("start", 0) + exposure.get("length", 1)
