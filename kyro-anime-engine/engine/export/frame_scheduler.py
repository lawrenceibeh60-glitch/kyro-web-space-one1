"""Deterministic frame scheduling for project exports."""


def frame_numbers(start, end, step=1):
    if start < 0 or end < start or step < 1:
        raise ValueError("Invalid frame range or step")
    return range(start, end + 1, step)


def schedule_frames(start, end, fps, step=1):
    if fps <= 0:
        raise ValueError("fps must be positive")
    return [{"frame": frame, "time": frame / fps}
            for frame in frame_numbers(start, end, step)]
