"""Cross-view landmark consistency checks."""


def compare_landmarks(reference, candidate, tolerance=1e-6):
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    issues = []
    if set(reference) != set(candidate):
        issues.append("Landmark names differ")
    for name in set(reference) & set(candidate):
        if len(reference[name]) != len(candidate[name]):
            issues.append(f"Landmark dimension differs: {name}")
        elif any(abs(a - b) > tolerance for a, b in zip(reference[name], candidate[name])):
            issues.append(f"Landmark differs: {name}")
    return issues
