"""Stable identifier creation and validation."""
import re
import uuid

_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def is_valid_id(value):
    return isinstance(value, str) and _ID_PATTERN.fullmatch(value) is not None


def validate_id(value, *, field="id"):
    if not is_valid_id(value):
        from engine.core.errors import ValidationError
        raise ValidationError(f"{field}: expected 1..64 letters, digits, '_' or '-'")
    return value


def new_id(prefix="item"):
    safe_prefix = re.sub(r"[^A-Za-z0-9_-]+", "_", str(prefix)).strip("_-") or "item"
    return f"{safe_prefix[:40]}_{uuid.uuid4().hex[:16]}"
