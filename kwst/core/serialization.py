"""Serializacja dataclasses ↔ dict/JSON z kontrolą typów (bez zewnętrznych zależności)."""
from __future__ import annotations

import dataclasses
import enum
import json
import types
import typing
from typing import Any, get_args, get_origin, get_type_hints


def to_dict(obj: Any) -> Any:
    """Rekurencyjna konwersja dataclass/enum/list/dict do typów JSON."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_dict(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {str(k): to_dict(v) for k, v in obj.items()}
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            return None
        return obj
    return obj


_HINT_CACHE: dict[type, dict[str, Any]] = {}


def _hints(cls: type) -> dict[str, Any]:
    if cls not in _HINT_CACHE:
        _HINT_CACHE[cls] = get_type_hints(cls)
    return _HINT_CACHE[cls]


def _convert(tp: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        for a in args:
            try:
                return _convert(a, value)
            except (TypeError, ValueError, KeyError):
                continue
        raise ValueError(f"Nie można skonwertować {value!r} do {tp}")
    if origin in (list, typing.List):
        (inner,) = get_args(tp) or (Any,)
        return [_convert(inner, v) for v in value]
    if origin in (dict, typing.Dict):
        kt, vt = get_args(tp) or (Any, Any)
        return {_convert(kt, k): _convert(vt, v) for k, v in value.items()}
    if isinstance(tp, type):
        if dataclasses.is_dataclass(tp):
            return from_dict(tp, value)
        if issubclass(tp, enum.Enum):
            return tp(value)
        if tp is float:
            return float(value)
        if tp is int:
            return int(value)
        if tp is bool:
            return bool(value)
        if tp is str:
            return str(value)
    return value


def from_dict(cls: type, data: dict) -> Any:
    """Tworzy instancję dataclass ``cls`` z dict. Nieznane klucze są pomijane,
    brakujące przyjmują wartości domyślne (zgodność wstecz plików projektu)."""
    if not isinstance(data, dict):
        raise TypeError(f"Oczekiwano dict dla {cls.__name__}, otrzymano {type(data).__name__}")
    hints = _hints(cls)
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name in data:
            kwargs[f.name] = _convert(hints[f.name], data[f.name])
    return cls(**kwargs)


def dumps(obj: Any, indent: int = 2) -> str:
    return json.dumps(to_dict(obj), ensure_ascii=False, indent=indent, sort_keys=False)


def deep_copy(obj: Any) -> Any:
    """Głęboka kopia dataclass przez serializację (gwarantuje niezależność)."""
    return from_dict(type(obj), json.loads(json.dumps(to_dict(obj))))
