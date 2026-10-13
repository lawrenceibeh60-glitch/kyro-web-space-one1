"""Dialogue cues and subtitle timing helpers."""


def validate_cue(cue):
    if not isinstance(cue.get("text"), str) or not cue["text"].strip():
        raise ValueError("Dialogue cue requires non-empty text")
    start, end = float(cue["start"]), float(cue["end"])
    if start < 0 or end < start:
        raise ValueError("Dialogue cue timing is invalid")
    return {**cue, "start": start, "end": end}


def sort_cues(cues):
    return sorted((validate_cue(cue) for cue in cues), key=lambda cue: (cue["start"], cue["end"]))


def active_cue(cues, time):
    return next((cue for cue in cues if cue["start"] <= time < cue["end"]), None)
