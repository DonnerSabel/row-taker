from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

JsonObject: TypeAlias = Mapping[str, object]
JsonSequence: TypeAlias = Sequence[object]


def require_field(data: JsonObject, key: str, *, context: str) -> object:
    try:
        return data[key]
    except KeyError as exc:
        raise KeyError(f"{context}.{key} is required") from exc


def require_object(value: object, *, context: str) -> JsonObject:
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} must be an object, got {type(value).__name__}")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"{context} must use string keys")
    return value


def require_sequence(value: object, *, context: str) -> JsonSequence:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{context} must be a list, got {type(value).__name__}")
    return value


def require_str(value: object, *, context: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{context} must be a string, got {type(value).__name__}")
    return value


def require_int(value: object, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{context} must be an int, got {type(value).__name__}")
    return value


def require_bool(value: object, *, context: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{context} must be a bool, got {type(value).__name__}")
    return value


def optional_str(value: object, *, context: str) -> str | None:
    if value is None:
        return None
    return require_str(value, context=context)


def optional_int(value: object, *, context: str) -> int | None:
    if value is None:
        return None
    return require_int(value, context=context)
