"""Atomic JSON serialization helpers for the KAE project format."""
import os
import tempfile
from pathlib import Path
from engine.data.serialization import dumps


def write_json_document(path, payload, *, indent=2):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=target.parent,
            prefix=f".{target.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(dumps(payload, indent=indent))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    return target


def dump_project_document(payload, *, indent=2):
    from engine.data.serialization import dumps
    return dumps(payload, indent=indent)


def write_project_document(path, payload, *, validate=True):
    if validate:
        from engine.project.project_validator import require_valid_project
        require_valid_project(payload)
    return write_json_document(path, payload)
