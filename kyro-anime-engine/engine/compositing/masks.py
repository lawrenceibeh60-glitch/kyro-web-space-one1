"""Mask compositing and alpha-threshold utilities."""


def combine_alpha(alpha, mask, mode="multiply"):
    if len(alpha) != len(mask):
        raise ValueError("Alpha and mask buffers must have equal lengths")
    if mode == "multiply":
        return [a * m for a, m in zip(alpha, mask)]
    if mode == "add":
        return [min(1, a + m) for a, m in zip(alpha, mask)]
    if mode == "subtract":
        return [max(0, a - m) for a, m in zip(alpha, mask)]
    if mode == "replace":
        return list(mask)
    raise ValueError(f"Unsupported mask mode: {mode}")


def threshold(alpha, cutoff=0.5):
    return [1.0 if value >= cutoff else 0.0 for value in alpha]
