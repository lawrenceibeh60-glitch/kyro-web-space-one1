"""Reusable stylized hair style presets."""
STYLES = {
    "short": {"length": 0.35, "volume": 0.3, "layers": 2},
    "bob": {"length": 0.65, "volume": 0.45, "layers": 3},
    "long": {"length": 1.0, "volume": 0.35, "layers": 4},
    "spiky": {"length": 0.6, "volume": 0.8, "layers": 5},
}


def get_style(name):
    try:
        return dict(STYLES[name])
    except KeyError:
        raise ValueError(f"Unknown hair style: {name}") from None
