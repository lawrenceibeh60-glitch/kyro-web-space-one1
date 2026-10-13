"""Composite normalized RGBA pixels or whole same-sized buffers."""
from engine.compositing.alpha import over
from engine.compositing.blend_modes import blend


def composite_pixel(source, destination, *, mode="normal", opacity=1.0):
    opacity = max(0.0, min(1.0, opacity))
    mixed = blend(destination[:3], source[:3], mode)
    return over((*mixed, source[3] * opacity), destination)


def composite_layers(layers):
    if not layers:
        return []
    size = len(layers[0]["pixels"])
    if any(len(layer["pixels"]) != size for layer in layers):
        raise ValueError("All pixel buffers must have equal lengths")
    result = list(layers[0]["pixels"])
    for layer in layers[1:]:
        mode, opacity = layer.get("blend_mode", "normal"), layer.get("opacity", 1)
        result = [composite_pixel(src, dst, mode=mode, opacity=opacity)
                  for src, dst in zip(layer["pixels"], result)]
    return result
