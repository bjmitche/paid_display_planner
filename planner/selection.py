from __future__ import annotations

from collections.abc import Sequence


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
