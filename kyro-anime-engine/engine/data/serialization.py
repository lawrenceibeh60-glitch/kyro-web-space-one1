"""JSON-compatible serialization with finite-number and cycle checks."""
import json
import math
from engine.core.errors import SerializationError


def to_json_value(value, *, _seen=None):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SerializationError("JSON numbers must be finite")
        return value
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return to_json_value(value.to_dict(), _seen=_seen)
    if _seen is None:
        _seen = set()
    identity = id(value)
    if identity in _seen:
        raise SerializationError("Cyclic values cannot be serialized")
    if isinstance(value, dict):
        _seen.add(identity)
        try:
            if not all(isinstance(key, str) for key in value):
                raise SerializationError("JSON object keys must be strings")
            return {key: to_json_value(item, _seen=_seen) for key, item in value.items()}
        finally:
            _seen.remove(identity)
    if isinstance(value, (list, tuple)):
        _seen.add(identity)
        try:
            return [to_json_value(item, _seen=_seen) for item in value]
        finally:
            _seen.remove(identity)
    raise SerializationError(f"Unsupported JSON value: {type(value).__name__}")


def dumps(value, *, indent=2):
    try:
        return json.dumps(to_json_value(value), ensure_ascii=False, allow_nan=False, indent=indent)
    except (TypeError, ValueError) as error:
        raise SerializationError(str(error)) from error


def loads(text):
    def reject_constant(token):
        raise ValueError(f"Invalid JSON numeric constant: {token}")
    try:
        return json.loads(text, parse_constant=reject_constant)
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise SerializationError(f"Invalid JSON: {error}") from error
