"""Structured diagnostics for validation and runtime reporting."""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Diagnostic:
    message: str
    severity: str = "error"
    code: str = "engine"
    path: str = ""

    def __post_init__(self):
        if self.severity not in {"info", "warning", "error"}:
            raise ValueError("severity must be info, warning, or error")

    def to_dict(self):
        return asdict(self)


class DiagnosticBag:
    def __init__(self):
        self._items = []

    def add(self, message, severity="error", code="engine", path=""):
        item = Diagnostic(str(message), severity, code, path)
        self._items.append(item)
        return item

    def extend(self, diagnostics):
        self._items.extend(diagnostics)

    @property
    def items(self):
        return tuple(self._items)

    @property
    def has_errors(self):
        return any(item.severity == "error" for item in self._items)

    def clear(self):
        self._items.clear()

    def to_list(self):
        return [item.to_dict() for item in self._items]
