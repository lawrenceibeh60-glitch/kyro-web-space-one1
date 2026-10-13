"""Conversions between frames, seconds, and timecode."""


def frame_to_seconds(frame, fps):
    if fps <= 0:
        raise ValueError("fps must be positive")
    return frame / fps


def seconds_to_frame(seconds, fps, *, rounding="floor"):
    import math
    if fps <= 0 or seconds < 0:
        raise ValueError("seconds must be non-negative and fps positive")
    value = seconds * fps
    if rounding == "floor":
        return math.floor(value)
    if rounding == "ceil":
        return math.ceil(value)
    if rounding == "round":
        return round(value)
    raise ValueError("rounding must be floor, ceil, or round")


def frame_timecode(frame, fps):
    if fps <= 0 or frame < 0:
        raise ValueError("frame and fps must be non-negative and fps positive")
    seconds = frame // fps
    remainder = int(frame % fps)
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{remainder:02d}"
