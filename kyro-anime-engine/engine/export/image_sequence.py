"""engine/export/image_sequence.py - PNG sequence packed into a zip (stdlib only)."""
import zipfile


def build_zip(paths, out_path, base):
    # PNGs are already compressed, so store them as-is
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_STORED) as z:
        for i, p in enumerate(paths, 1):
            z.write(p, f"{base}_{i:04d}.png")
