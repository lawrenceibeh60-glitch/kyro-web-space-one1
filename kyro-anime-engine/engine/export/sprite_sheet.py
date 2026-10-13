"""engine/export/sprite_sheet.py - sprite sheet PNG + JSON atlas, zipped (needs Pillow)."""
import io
import json
import math
import zipfile

MAX_SIDE = 16384  # larger sheets fail in most game engines / GPUs


def build_sprite(paths, out_path, base, columns=0, padding=0, fps=12):
    from PIL import Image
    imgs = []
    for p in paths:
        with Image.open(p) as im:
            imgs.append(im.convert("RGBA"))
    w, h = imgs[0].size
    if any(i.size != (w, h) for i in imgs):
        raise ValueError("All frames must have the same size")
    n = len(imgs)
    cols = min(columns, n) if columns and columns > 0 else math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    pad = max(0, int(padding))
    sheet_w, sheet_h = cols * w + (cols - 1) * pad, rows * h + (rows - 1) * pad
    if sheet_w > MAX_SIDE or sheet_h > MAX_SIDE:
        raise ValueError(f"Sprite sheet would be {sheet_w}x{sheet_h}px (max {MAX_SIDE}). Lower the scale or use more columns.")
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (0, 0, 0, 0))
    frames = []
    for i, im in enumerate(imgs):
        x, y = (i % cols) * (w + pad), (i // cols) * (h + pad)
        sheet.paste(im, (x, y))
        frames.append({"index": i, "x": x, "y": y, "w": w, "h": h})
    atlas = {
        "image": f"{base}_sprite.png", "frame_width": w, "frame_height": h, "columns": cols, "rows": rows,
        "padding": pad, "fps": fps, "frame_count": n, "frames": frames,
    }
    buf = io.BytesIO()
    sheet.save(buf, "PNG")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{base}_sprite.png", buf.getvalue())
        z.writestr(f"{base}_sprite.json", json.dumps(atlas, indent=2))
