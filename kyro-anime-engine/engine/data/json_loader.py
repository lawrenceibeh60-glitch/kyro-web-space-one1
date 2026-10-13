"""Load JSON documents from disk with explicit parsing errors."""
from pathlib import Path
from engine.core.errors import SerializationError
from engine.data.serialization import loads


def load_json_document(path):
    source = Path(path)
    try:
        return loads(source.read_text(encoding="utf-8"))
    except OSError as error:
        raise SerializationError(f"Could not read {source}: {error}") from error


def load_project_document(path):
    document = load_json_document(path)
    if not isinstance(document, dict):
        raise SerializationError(f"Project file must contain a JSON object: {path}")
    return document


def import_project_payload(payload):
    if not isinstance(payload, dict):
        raise SerializationError("Imported project payload must be a JSON object")
    return payload


def load_json(path, *, encoding="utf-8"):
    source = Path(path)
    try:
        return loads(source.read_text(encoding=encoding))
    except OSError as error:
        raise SerializationError(f"Could not read {source}: {error}") from error


def load_project(path, *, normalize=True):
    project = load_project_document(path)
    if normalize:
        from engine.data.normalizer import normalize_project
        return normalize_project(project)
    return project
