"""Stable z-ordered render queue."""


class RenderQueue:
    def __init__(self):
        self._commands = []

    def submit(self, command):
        self._commands.append(command)
        return command

    def extend(self, commands):
        self._commands.extend(commands)

    def ordered(self):
        return [item for _, item in sorted(
            enumerate(self._commands),
            key=lambda pair: (getattr(pair[1], "z", 0), pair[0]),
        )]

    def clear(self):
        self._commands.clear()

    def __len__(self):
        return len(self._commands)
