"""Depth sorting and simple atmospheric depth attenuation."""


def composite_order(layers):
    return sorted(enumerate(layers), key=lambda pair: (pair[1].get("depth", 1), pair[0]))


def depth_opacity(depth, *, near=0, far=1, minimum=0.0):
    if far <= near:
        raise ValueError("far depth must exceed near depth")
    amount = max(0.0, min(1.0, (depth - near) / (far - near)))
    return 1 - amount * (1 - minimum)
