from dataclasses import fields, is_dataclass
from datetime import datetime
from typing import Any


def serialize(value: Any) -> Any:
    """Recursively convert SDK values into JSON-serializable Python objects."""
    if isinstance(value, datetime):
        return value.isoformat()

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: serialize(getattr(value, field.name)) for field in fields(value)
        }

    if isinstance(value, list):
        return [serialize(item) for item in value]

    if isinstance(value, tuple):
        return [serialize(item) for item in value]

    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}

    return value
