"""Exposure-sheet lookup, validation, and frame splitting."""


def drawing_at(exposures, frame):
    for exposure in exposures:
        start, length = exposure.get("start", 0), exposure.get("length", 1)
        if start <= frame < start + length:
            return exposure.get("drawing")
    return None


def validate_exposures(exposures, *, duration=None):
    errors, previous_end = [], 0
    for index, exposure in enumerate(exposures):
        start, length = exposure.get("start"), exposure.get("length")
        if not isinstance(start, int) or start < 0:
            errors.append(f"exposures[{index}].start: non-negative integer required")
            continue
        if not isinstance(length, int) or length < 1:
            errors.append(f"exposures[{index}].length: positive integer required")
            continue
        if start < previous_end:
            errors.append(f"exposures[{index}]: overlaps previous exposure")
        if duration is not None and start + length > duration:
            errors.append(f"exposures[{index}]: exceeds timeline duration")
        previous_end = start + length
    return errors


def split_exposure(exposure, frame):
    start, end = exposure["start"], exposure["start"] + exposure["length"]
    if not start < frame < end:
        return [dict(exposure)]
    left, right = dict(exposure), dict(exposure)
    left["length"], right["start"], right["length"] = frame - start, frame, end - frame
    return [left, right]
