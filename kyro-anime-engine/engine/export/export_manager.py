"""engine/export/export_manager.py - picks the encoder for a job and writes the result atomically."""
import os


def has_pillow():
    try:
        import PIL.Image  # noqa: F401
        return True
    except ImportError:
        return False


def output_name(fmt, base):
    return {"png": f"{base}_png.zip", "gif": f"{base}.gif", "sprite": f"{base}_sprite.zip"}[fmt]


def build(paths, out_dir, job):
    """Encode `paths` (PNG frames) per `job`; returns the output file name inside out_dir."""
    from engine.export import gif_export, image_sequence, sprite_sheet
    fmt, base = job["format"], job["base"]
    name = output_name(fmt, base)
    final, tmp = out_dir / name, out_dir / (name + ".part")
    try:
        if fmt == "png":
            image_sequence.build_zip(paths, tmp, base)
        elif fmt == "gif":
            gif_export.build_gif(paths, tmp, job["fps"], job.get("loop", True), job.get("transparent", False))
        else:
            sprite_sheet.build_sprite(paths, tmp, base, job.get("columns", 0), job.get("padding", 0), job["fps"])
        os.replace(tmp, final)
    finally:
        if tmp.exists():
            tmp.unlink()
    return name
