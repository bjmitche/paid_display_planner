from __future__ import annotations

from collections.abc import Iterable, Sequence


def unique_ids(values: Iterable[object]) -> list[object]:
    return list(dict.fromkeys(values))


def resolve_choice_index(
    chosen: object,
    options: Sequence[object],
    default_index: int = 0,
) -> int:
    if chosen in options:
        return list(options).index(chosen)
    if not options:
        raise ValueError("no choices available")
    return min(max(default_index, 0), len(options) - 1)
