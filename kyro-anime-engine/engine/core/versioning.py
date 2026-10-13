"""Format version helpers for engine-readable documents."""
from engine.core.errors import ValidationError


def read_version(document, *, default=None):
    version = document.get("version", default) if isinstance(document, dict) else default
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValidationError("Document version must be a positive integer")
    return version


def ensure_supported_version(document, current, *, minimum=1):
    version = read_version(document)
    if version < minimum or version > current:
        raise ValidationError(f"Unsupported document version {version}; supported range is {minimum}..{current}")
    return version
