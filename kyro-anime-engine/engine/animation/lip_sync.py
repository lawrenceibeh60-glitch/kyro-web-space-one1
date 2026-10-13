"""Convert amplitude samples or phoneme cues into mouth exposure keys."""


def amplitude_to_mouth(samples, *, threshold=0.15):
    result = []
    for frame, amplitude in enumerate(samples):
        shape = "open" if amplitude >= threshold else "closed"
        if not result or result[-1]["shape"] != shape:
            result.append({"frame": frame, "shape": shape})
    return result


def cues_to_track(cues, *, fps, duration_frames=None):
    if fps <= 0:
        raise ValueError("fps must be positive")
    keys = []
    for cue in cues:
        frame = max(0, round(float(cue["time"]) * fps))
        if duration_frames is not None:
            frame = min(frame, max(0, duration_frames - 1))
        shape = cue.get("shape", cue.get("phoneme", "closed"))
        if not keys or frame > keys[-1]["t"]:
            keys.append({"t": frame, "v": shape, "ease": "hold"})
        else:
            keys[-1] = {"t": frame, "v": shape, "ease": "hold"}
    return keys
