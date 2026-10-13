"""Apply explicit bounds and cross-parameter constraints."""


def clamp_parameters(values, bounds):
    result = dict(values)
    for name, (minimum, maximum) in bounds.items():
        if minimum > maximum:
            raise ValueError(f"Invalid bounds for {name}")
        if name in result:
            result[name] = max(minimum, min(maximum, result[name]))
    return result


def satisfy_constraints(values, constraints):
    failures = [name for name, predicate in constraints.items() if not predicate(values)]
    if failures:
        raise ValueError("Unsatisfied constraints: " + ", ".join(failures))
    return values
