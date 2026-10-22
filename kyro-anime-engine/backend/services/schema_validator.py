import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

_SCHEMAS_DIR = Path(__file__).resolve().parent.parent.parent / "formats" / "schemas"
_SCHEMA_NAMES = (
    "animation.schema.json",
    "character.schema.json",
    "drawing.schema.json",
    "effects.schema.json",
    "path.schema.json",
    "project.schema.json",
    "node_graph.schema.json",
    "rig.schema.json",
    "scene.schema.json",
    "style.schema.json",
)


def _load_schema(name):
    with open(_SCHEMAS_DIR / name, encoding="utf-8") as f:
        return json.load(f)


_SCHEMAS = {name: _load_schema(name) for name in _SCHEMA_NAMES}
_DRAWING_SCHEMA = _SCHEMAS["drawing.schema.json"]
_PATH_SCHEMA = _SCHEMAS["path.schema.json"]

_REGISTRY = Registry().with_resources(
    (name, Resource.from_contents(schema))
    for name, schema in _SCHEMAS.items()
)

_DRAWING_VALIDATOR = Draft202012Validator(_DRAWING_SCHEMA, registry=_REGISTRY)
_PATH_VALIDATOR = Draft202012Validator(_PATH_SCHEMA, registry=_REGISTRY)
_PROJECT_VALIDATOR = Draft202012Validator(_SCHEMAS["project.schema.json"], registry=_REGISTRY)


def _format_error(error):
    location = "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}"
        for part in error.absolute_path
    )
    return f"{location}: {error.message}"


class SchemaValidator:
    def validate_schema(self, instance, schema):
        """Validate an instance against a schema using Draft 2020-12."""
        validator = Draft202012Validator(schema, registry=_REGISTRY)
        errors = list(validator.iter_errors(instance))
        if errors:
            return False, "; ".join(str(e.message) for e in errors[:5])
        return True, None

    def validate_drawing(self, drawing):
        """Validate a drawing against the drawing schema."""
        errors = list(_DRAWING_VALIDATOR.iter_errors(drawing))
        if errors:
            return False, "; ".join(str(e.message) for e in errors[:5])
        return True, None

    def validate_path(self, path):
        """Validate a path against the path schema."""
        errors = list(_PATH_VALIDATOR.iter_errors(path))
        if errors:
            return False, "; ".join(str(e.message) for e in errors[:5])
        return True, None

    def validate_project(self, project):
        """Validate a complete KAE project document against the canonical schema."""
        errors = list(_PROJECT_VALIDATOR.iter_errors(project))
        if errors:
            return False, "; ".join(_format_error(error) for error in errors[:5])
        return True, None


validator = SchemaValidator()