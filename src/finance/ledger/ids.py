"""Entry ids: ULIDs (sortable by creation time)."""

from ulid import ULID


def new_id() -> str:
    return str(ULID())
