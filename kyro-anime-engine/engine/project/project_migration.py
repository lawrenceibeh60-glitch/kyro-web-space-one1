"""Incremental migrations for supported KAE document versions."""
from copy import deepcopy
from engine.core.errors import ValidationError
from engine.data.normalizer import normalize_project

CURRENT_VERSION = 1


def migrate_project(document, *, target_version=CURRENT_VERSION):
    if not isinstance(document, dict):
        raise ValidationError("Project document must be an object")
    migrated = deepcopy(document)
    version = migrated.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValidationError("Project version must be a positive integer")
    if version > target_version:
        raise ValidationError(f"Project version {version} is newer than supported version {target_version}")
    migrated["version"] = target_version
    return normalize_project(migrated)
