"""Premultiplied-alpha compositing primitives."""


def over(source, destination):
    sr, sg, sb, sa = source
    dr, dg, db, da = destination
    out_alpha = sa + da * (1 - sa)
    if out_alpha <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    return (
        (sr * sa + dr * da * (1 - sa)) / out_alpha,
        (sg * sa + dg * da * (1 - sa)) / out_alpha,
        (sb * sa + db * da * (1 - sa)) / out_alpha,
        out_alpha,
    )


def apply_opacity(color, opacity):
    opacity = max(0.0, min(1.0, opacity))
    return (*color[:3], color[3] * opacity if len(color) > 3 else opacity)
