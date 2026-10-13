"""Discover and cache the repository's canonical JSON schemas."""
import json
from pathlib import Path
from engine.core.errors import MissingResourceError, SerializationError


class SchemaRegistry:
    def __init__(self, schema_dir=None):
        self.schema_dir = Path(schema_dir) if schema_dir else Path(__file__).resolve().parents[2] / "formats" / "schemas"
        self._schemas = {}

    def register(self, name, schema):
        self._schemas[name] = schema

    def get(self, name):
        if name in self._schemas:
            return self._schemas[name]
        path = self.schema_dir / name
        if path.suffix != ".json":
            path = path.with_suffix(".schema.json")
        if not path.is_file():
            raise MissingResourceError(f"Schema not found: {name}")
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SerializationError(f"Could not load schema {path}: {error}") from error
        self._schemas[name] = schema
        return schema

    def names(self):
        return tuple(sorted(self._schemas))
