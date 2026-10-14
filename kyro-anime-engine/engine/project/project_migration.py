"""Incremental migrations for supported KAE document versions."""
from copy import deepcopy
from engine.core.errors import ValidationError
from engine.data.normalizer import normalize_project

CURRENT_VERSION = 2


def migrate_project(document, *, target_version=CURRENT_VERSION):
    if not isinstance(document, dict):
        raise ValidationError("Project document must be an object")
    migrated = deepcopy(document)
    version = migrated.get("version", 1)
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise ValidationError("Project version must be a positive integer")
    if isinstance(target_version, bool) or not isinstance(target_version, int) or target_version < 1:
        raise ValidationError("Migration target version must be a positive integer")
    if version > target_version:
        raise ValidationError(f"Project version {version} is newer than supported version {target_version}")
    while version < target_version:
        if version == 1:
            migrated.setdefault("styles", [])
            version = 2
            migrated["version"] = version
        else:
            raise ValidationError(f"No migration is available from project version {version}")
    migrated["version"] = version
    return normalize_project(migrated)
