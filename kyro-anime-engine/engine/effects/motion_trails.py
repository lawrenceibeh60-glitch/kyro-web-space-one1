"""Extract faded trail samples from prior frame positions."""


def trail_samples(history, frame, *, count=6, spacing=1, decay=0.72):
    if count < 0 or spacing < 1 or not 0 <= decay <= 1:
        raise ValueError("Invalid trail sampling options")
    result = []
    for index in range(1, count + 1):
        sample_frame = frame - index * spacing
        if sample_frame < 0:
            break
        value = history(sample_frame) if callable(history) else history.get(sample_frame)
        if value is not None:
            result.append({"frame": sample_frame, "value": value, "opacity": decay ** index})
    return result
