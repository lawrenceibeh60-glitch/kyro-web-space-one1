"""Frame-window and normalized-age helpers for timed effects."""


def active(effect, frame):
    return effect.get("enabled", True) and effect.get("start_frame", 0) <= frame <= effect.get("end_frame", float("inf"))


def progress(effect, frame):
    start = effect.get("start_frame", 0)
    end = effect.get("end_frame", start)
    if frame < start or frame > end:
        return None
    return 1.0 if end == start else (frame - start) / (end - start)


def active_effects(effects, frame):
    return [effect for effect in effects if active(effect, frame)]
