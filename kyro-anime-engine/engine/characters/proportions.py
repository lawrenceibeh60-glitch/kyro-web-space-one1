"""Normalized stylized character proportions."""
DEFAULT_PROPORTIONS = {
    "head": 1.0, "torso": 2.0, "arm": 1.7, "leg": 2.5,
    "shoulder_width": 1.2, "hip_width": 1.0,
}


def normalize_proportions(values=None):
    result = {**DEFAULT_PROPORTIONS, **(values or {})}
    if any(not isinstance(value, (int, float)) or value <= 0 for value in result.values()):
        raise ValueError("Proportions must be positive numbers")
    scale = result["head"]
    return {key: value / scale for key, value in result.items()}


def total_height(proportions):
    return proportions["head"] + proportions["torso"] + proportions["leg"]
