"""Create bounded numeric variants from a stable base."""


def vary_parameters(rng, parameters, amount=0.1, bounds=None):
    if amount < 0:
        raise ValueError("amount must be non-negative")
    bounds = bounds or {}
    result = {}
    for name, value in parameters.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            candidate = value + rng.uniform(-amount, amount) * max(abs(value), 1)
            if name in bounds:
                candidate = max(bounds[name][0], min(bounds[name][1], candidate))
            result[name] = candidate
        else:
            result[name] = value
    return result
