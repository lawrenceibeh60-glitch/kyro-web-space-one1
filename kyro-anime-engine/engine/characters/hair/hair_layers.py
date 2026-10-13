"""Ordered hair layer stacking."""


def sort_layers(layers):
    return sorted(layers, key=lambda layer: (layer.get("depth", 0), layer.get("id", "")))


def insert_layer(layers, layer):
    if any(existing.get("id") == layer.get("id") for existing in layers):
        raise ValueError(f"Duplicate hair layer id: {layer.get('id')}")
    return sort_layers([*layers, layer])
