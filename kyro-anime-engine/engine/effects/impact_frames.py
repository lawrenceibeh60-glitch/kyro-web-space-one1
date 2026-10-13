"""Generate hold and smear frame schedules for impact animation."""


def schedule(start_frame, *, hold=1, smear=1, recovery=2):
    if start_frame < 0 or min(hold, smear, recovery) < 0:
        raise ValueError("Frame and durations must be non-negative")
    frames = []
    for offset in range(hold):
        frames.append({"frame": start_frame + offset, "phase": "impact", "weight": 1.0})
    base = start_frame + hold
    for offset in range(smear):
        frames.append({"frame": base + offset, "phase": "smear", "weight": 1 - offset / max(smear, 1)})
    base += smear
    for offset in range(recovery):
        frames.append({"frame": base + offset, "phase": "recovery", "weight": (offset + 1) / max(recovery, 1)})
    return frames
