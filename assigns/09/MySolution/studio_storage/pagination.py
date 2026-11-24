"""Keep cursor chains over immutable records for the life of the process."""

from dataclasses import dataclass, field
from uuid import uuid4

from .errors import invalid_request


@dataclass(slots=True)
class _Snapshot[Record]:
    items: tuple[Record, ...]
    tokens: dict[tuple[int, int], str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _Cursor[Record]:
    snapshot: _Snapshot[Record]
    size: int
    offset: int


class Paginator[Record]:
    """Paginate one resource while the caller holds the store lock."""

    def __init__(self) -> None:
        self._latest: _Snapshot[Record] | None = None
        self._cursors: dict[str, _Cursor[Record]] = {}

    def first_page(self, items: tuple[Record, ...], size: int) -> tuple[tuple[Record, ...], str | None]:
        if self._latest is None or self._latest.items != items:
            self._latest = _Snapshot(items)
        return self._page(self._latest, size, 0)

    def continue_page(self, token: str, size: int | None) -> tuple[tuple[Record, ...], str | None]:
        cursor = self._cursors.get(token)
        if cursor is None:
            raise invalid_request("cursor is unknown for this resource.")
        if size is not None and size != cursor.size:
            raise invalid_request("limit must match the cursor's original page size.")
        return self._page(cursor.snapshot, cursor.size, cursor.offset)

    def _page(
        self, snapshot: _Snapshot[Record], size: int, offset: int
    ) -> tuple[tuple[Record, ...], str | None]:
        end = offset + size
        items = snapshot.items[offset:end]
        if end >= len(snapshot.items):
            return items, None

        position = (size, end)
        token = snapshot.tokens.get(position)
        if token is None:
            token = uuid4().hex
            self._cursors[token] = _Cursor(snapshot, size, end)
            snapshot.tokens[position] = token
        return items, token
