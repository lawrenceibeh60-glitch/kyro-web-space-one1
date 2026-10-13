"""engine/export/gif_export.py - animated GIF from PNG frames (needs Pillow)."""


def durations(n, fps):
    """Per-frame delays in ms (GIF uses 10 ms steps). Cumulative rounding keeps the total length exact."""
    out, prev = [], 0
    for i in range(1, n + 1):
        t = int(round(i * 1000.0 / fps / 10.0)) * 10
        d = max(20, t - prev)  # browsers clamp anything below 20 ms
        out.append(d)
        prev += d
    return out


def _prepare(path, transparent):
    from PIL import Image
    with Image.open(path) as im:
        img = im.convert("RGBA")
    if not transparent:
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        return bg.convert("RGB").quantize(colors=256, dither=0)
    alpha = img.getchannel("A")
    p = img.convert("RGB").quantize(colors=255, dither=0)  # index 255 is kept for "transparent"
    pal = (p.getpalette() or [])[:768]
    pal += [0] * (768 - len(pal))
    p.putpalette(pal)
    p.paste(255, mask=alpha.point(lambda a: 255 if a < 128 else 0))
    p.info["transparency"] = 255
    return p


def build_gif(paths, out_path, fps, loop=True, transparent=False):
    from PIL import Image
    frames = [_prepare(p, transparent) for p in paths]
    sizes = {f.size for f in frames}
    if len(sizes) != 1:
        raise ValueError("All frames must have the same size")
    kw = {"save_all": True, "append_images": frames[1:], "duration": durations(len(frames), fps), "optimize": False}
    if loop:
        kw["loop"] = 0  # forever
    if transparent:
        kw["transparency"] = 255
        kw["disposal"] = 2  # clear each frame so transparent areas don't ghost
    frames[0].save(out_path, "GIF", **kw)
