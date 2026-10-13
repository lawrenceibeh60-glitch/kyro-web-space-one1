"""Frame/sample synchronization and audio clip alignment."""


def frame_to_time(frame, fps):
    if frame < 0 or fps <= 0:
        raise ValueError("Frame must be non-negative and fps positive")
    return frame / fps


def time_to_frame(time, fps):
    if time < 0 or fps <= 0:
        raise ValueError("Time must be non-negative and fps positive")
    return round(time * fps)


def time_to_sample(time, sample_rate):
    if time < 0 or sample_rate <= 0:
        raise ValueError("Time must be non-negative and sample rate positive")
    return round(time * sample_rate)


def align_clips(clips, fps):
    return [{**clip, "start_frame": time_to_frame(clip["start"], fps),
             "end_frame": time_to_frame(clip["start"] + clip["duration"], fps)}
            for clip in clips]
