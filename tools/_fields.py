"""Shared field checks for tool args."""

from __future__ import annotations

from typing import Iterable, List, Optional, Union

from constants import ITEM_ID_RE


def item_id(value: Optional[str], *, field_name: str) -> Optional[str]:
    if value is not None and not ITEM_ID_RE.match(value):
        raise ValueError(
            f"{field_name} must be a DB item id matching itm_[0-9a-f]{{16}}; got {value!r}"
        )
    return value


def one_of(value: Optional[str], allowed: frozenset, *, field_name: str) -> Optional[str]:
    if value is not None and value not in allowed:
        raise ValueError(f"{field_name} must be one of {sorted(allowed)}; got {value!r}")
    return value


def all_one_of(
    values: Optional[List[str]], allowed: frozenset, *, field_name: str
) -> Optional[List[str]]:
    if values is not None:
        for value in values:
            one_of(value, allowed, field_name=field_name)
    return values


def non_empty(value: Optional[str], *, field_name: str) -> Optional[str]:
    if value is not None and not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def as_list(value: Union[None, str, Iterable[str]]) -> Union[None, List[str]]:
    """Small models often send one filter value as a bare string."""
    if isinstance(value, str):
        return [value]
    return value
