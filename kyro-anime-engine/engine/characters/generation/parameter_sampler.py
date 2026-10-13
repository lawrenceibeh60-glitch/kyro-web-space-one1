"""Sample constrained numeric and categorical generation parameters."""


def sample_range(rng, minimum, maximum, *, step=None):
    if minimum > maximum:
        raise ValueError("minimum must not exceed maximum")
    value = rng.uniform(minimum, maximum)
    if step is not None:
        if step <= 0:
            raise ValueError("step must be positive")
        value = minimum + round((value - minimum) / step) * step
    return min(maximum, value)


def choose(rng, options, weights=None):
    if not options:
        raise ValueError("options must not be empty")
    return rng.choices(options, weights=weights, k=1)[0] if weights else rng.choice(options)
