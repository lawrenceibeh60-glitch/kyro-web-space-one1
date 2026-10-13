"""Dependency-free JSON Schema subset validator for local schema documents."""
import math
import re


def validate_schema(value, schema, *, path="$"):
    errors = []
    if not isinstance(schema, dict):
        return [f"{path}: schema must be an object"]
    expected = schema.get("type")
    type_matches = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item),
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
    }
    if isinstance(expected, list):
        valid = any(type_matches.get(kind, lambda _: False)(value) for kind in expected)
    else:
        valid = expected is None or type_matches.get(expected, lambda _: False)(value)
    if not valid:
        return [f"{path}: expected {expected}"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value is not in the allowed set")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required")
        properties = schema.get("properties", {})
        for key, child in value.items():
            if key in properties:
                errors.extend(validate_schema(child, properties[key], path=f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: additional property is not allowed")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: requires at least {schema['minItems']} items")
        if len(value) > schema.get("maxItems", math.inf):
            errors.append(f"{path}: allows at most {schema['maxItems']} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(validate_schema(item, item_schema, path=f"{path}[{index}]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string is too short")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            errors.append(f"{path}: does not match the required pattern")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        for bound, fails in (
            ("minimum", lambda x: value < x),
            ("maximum", lambda x: value > x),
            ("exclusiveMinimum", lambda x: value <= x),
            ("exclusiveMaximum", lambda x: value >= x),
        ):
            if bound in schema and fails(schema[bound]):
                errors.append(f"{path}: violates {bound}={schema[bound]}")
    return errors
