"""Frame-triggered event dispatch with loop and reverse-playback support."""


def events_between(events, previous_frame, current_frame, *, loop_duration=None):
    if current_frame == previous_frame:
        return []
    if current_frame > previous_frame:
        if loop_duration and current_frame // loop_duration != previous_frame // loop_duration:
            return sorted(
                [event for event in events if event.get("frame", -1) > previous_frame % loop_duration]
                + [event for event in events if event.get("frame", -1) <= current_frame % loop_duration],
                key=lambda event: event.get("frame", 0),
            )
        return [event for event in sorted(events, key=lambda item: item.get("frame", 0))
                if previous_frame < event.get("frame", -1) <= current_frame]
    return [event for event in sorted(events, key=lambda item: item.get("frame", 0), reverse=True)
            if current_frame <= event.get("frame", -1) < previous_frame]


def dispatch(events, bus, previous_frame, current_frame, **options):
    triggered = events_between(events, previous_frame, current_frame, **options)
    for event in triggered:
        bus.emit(event.get("name", "animation:event"), event)
    return triggered
