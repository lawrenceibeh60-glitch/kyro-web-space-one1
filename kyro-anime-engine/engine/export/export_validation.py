"""Validate common frame export settings."""


def validate_export(settings):
    errors = []
    for dimension in ("width", "height"):
        if not isinstance(settings.get(dimension), int) or settings[dimension] <= 0:
            errors.append(f"{dimension} must be a positive integer")
    fps = settings.get("fps")
    if not isinstance(fps, (int, float)) or fps <= 0:
        errors.append("fps must be positive")
    if settings.get("start_frame", 0) < 0:
        errors.append("start_frame must be non-negative")
    if settings.get("end_frame", 0) < settings.get("start_frame", 0):
        errors.append("end_frame must not precede start_frame")
    if errors:
        raise ValueError("; ".join(errors))
    return True
