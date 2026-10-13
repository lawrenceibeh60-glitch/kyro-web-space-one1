"""Expression presets as facial feature offsets."""
EXPRESSIONS = {
    "neutral": {"brow": 0.0, "eye_open": 1.0, "mouth_open": 0.0, "smile": 0.0},
    "happy": {"brow": 0.12, "eye_open": 0.8, "mouth_open": 0.25, "smile": 0.7},
    "sad": {"brow": -0.2, "eye_open": 0.75, "mouth_open": 0.05, "smile": -0.5},
    "angry": {"brow": -0.3, "eye_open": 0.65, "mouth_open": 0.1, "smile": -0.3},
    "surprised": {"brow": 0.3, "eye_open": 1.0, "mouth_open": 0.6, "smile": 0.0},
}


def get_expression(name):
    try:
        return dict(EXPRESSIONS[name])
    except KeyError:
        raise ValueError(f"Unknown expression: {name}") from None


def blend_expressions(first, second, amount):
    if not 0 <= amount <= 1:
        raise ValueError("amount must be between 0 and 1")
    a, b = get_expression(first), get_expression(second)
    return {key: a[key] + (b[key] - a[key]) * amount for key in a}
