"""Procedural hair lock generation from a style preset."""
from engine.characters.hair.hair_locks import lock_curve
from engine.characters.hair.hair_styles import get_style


def generate_hairline(center, width, style="bob", *, color="#302020", locks=9):
    preset = get_style(style)
    if locks < 1:
        raise ValueError("locks must be positive")
    cx, cy = center
    strands = []
    for index in range(locks):
        t = index / max(locks - 1, 1) - 0.5
        root = (cx + t * width * 0.9, cy)
        angle = -90 + t * 60
        strands.append({"points": lock_curve(root, preset["length"] * width * 0.5, angle),
                        "color": color, "depth": index})
    return {"style": style, "strands": strands, "volume": preset["volume"]}
