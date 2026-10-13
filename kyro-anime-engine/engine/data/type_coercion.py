"""Explicit, safe coercion helpers used while loading JSON documents."""
import math
from engine.core.errors import ValidationError


def to_number(value, *, field="value", minimum=None, maximum=None):
    if isinstance(value, bool):
        raise ValidationError(f"{field}: expected a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValidationError(f"{field}: expected a finite number") from error
    if not math.isfinite(result) or (minimum is not None and result < minimum) or (maximum is not None and result > maximum):
        raise ValidationError(f"{field}: number is outside the supported range")
    return result


def to_integer(value, *, field="value", minimum=None, maximum=None):
    number = to_number(value, field=field, minimum=minimum, maximum=maximum)
    if not number.is_integer():
        raise ValidationError(f"{field}: expected an integer")
    return int(number)


def to_boolean(value, *, field="value"):
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    raise ValidationError(f"{field}: expected a boolean")


def to_string(value, *, field="value", allow_empty=True):
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ValidationError(f"{field}: expected a string")
    return value
