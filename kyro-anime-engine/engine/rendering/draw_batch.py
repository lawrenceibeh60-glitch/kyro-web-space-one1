"""Batch compatible commands to reduce backend state changes."""


def batch_commands(commands):
    batches, lookup = [], {}
    for command in commands:
        key = (
            getattr(command, "kind", None), getattr(command, "color", None),
            getattr(command, "fill", None), getattr(command, "width", None),
            getattr(command, "opacity", None), getattr(command, "z", None),
        )
        if key not in lookup:
            lookup[key] = len(batches)
            batches.append({"state": key, "commands": []})
        batches[lookup[key]]["commands"].append(command)
    return batches
