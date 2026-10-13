"""Generate coordinated garment records from outfit templates."""
from engine.characters.clothing.garment import Garment


TEMPLATES = {
    "casual": (("top", "#4b83bd"), ("bottom", "#303b52")),
    "uniform": (("jacket", "#26385f"), ("bottom", "#26385f")),
    "dress": (("dress", "#bd5478"),),
}


def generate_outfit(style="casual", prefix="garment"):
    if style not in TEMPLATES:
        raise ValueError(f"Unknown outfit style: {style}")
    return [Garment(f"{prefix}-{index}", kind, color)
            for index, (kind, color) in enumerate(TEMPLATES[style])]
