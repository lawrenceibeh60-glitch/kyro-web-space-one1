"""Supersampling helpers for high-quality raster output."""


def supersampled_size(width, height, factor=2):
    if min(width, height, factor) < 1:
        raise ValueError("Dimensions and supersample factor must be positive")
    return width * factor, height * factor


def scale_points(points, factor):
    return [(point[0] * factor, point[1] * factor, *point[2:]) for point in points]


def downsample(image, size):
    try:
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("Pillow is required for downsampling raster images") from error
    return image.resize(size, Image.Resampling.LANCZOS)
