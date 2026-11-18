"""Manage process-local cursors for the fixed queens search."""

from collections.abc import Callable
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import NamedTuple
from uuid import uuid4

from .solver import L, Event, QueensSolver, force_event


MIN_LIMIT = 1
MAX_LIMIT = 32
INACTIVITY_SECONDS = 300


class StreamNotFound(LookupError):
    """The stream ID is unknown, closed, or expired."""


class InvalidStreamInput(ValueError):
    """The stream ID or event limit has an invalid value."""


class EventBatch(NamedTuple):
    events: list[Event]
    done: bool


@dataclass(frozen=True, slots=True)
class _Stream:
    cursor: L.D0Vlazy | None  # None marks an exhausted stream.
    expires_at: float


class StreamTable:
    """Own the cursors and serialize changes to their published positions."""

    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._solver = QueensSolver()
        self._streams: dict[str, _Stream] = {}
        self._lock = Lock()

    def open(self, size: object) -> str:
        cursor = self._solver.open(size)
        stream_id = str(uuid4())
        with self._lock:
            now = self._clock()
            self._sweep_expired(now)
            self._streams[stream_id] = _Stream(cursor, now + INACTIVITY_SECONDS)
        return stream_id

    def next(self, stream_id: object, limit: object) -> EventBatch:
        stream_id = _validate_stream_id(stream_id)
        if type(limit) is not int or not MIN_LIMIT <= limit <= MAX_LIMIT:
            raise InvalidStreamInput("Event limit must be an integer from 1 through 32")

        with self._lock:
            cursor = self._lookup(stream_id).cursor
            events: list[Event] = []
            for _ in range(limit):
                if cursor is None:
                    break
                step = force_event(cursor)
                if step is None:
                    raise RuntimeError("Queens event stream ended without done")
                event, cursor = step
                events.append(event)
                if event["event"] == "done":
                    cursor = None
                    break

            # A failed force can memoize cells, but the published cursor still
            # points to the beginning of the unread batch.
            batch = EventBatch(events, done=cursor is None)
            self._streams[stream_id] = _Stream(cursor, self._clock() + INACTIVITY_SECONDS)
            return batch

    def close(self, stream_id: object) -> None:
        stream_id = _validate_stream_id(stream_id)
        with self._lock:
            self._lookup(stream_id)
            del self._streams[stream_id]

    def _lookup(self, stream_id: str) -> _Stream:
        self._sweep_expired(self._clock())
        stream = self._streams.get(stream_id)
        if stream is None:
            raise StreamNotFound("Stream not found")
        return stream

    def _sweep_expired(self, now: float) -> None:
        expired = [stream_id for stream_id, stream in self._streams.items() if stream.expires_at <= now]
        for stream_id in expired:
            del self._streams[stream_id]


def _validate_stream_id(stream_id: object) -> str:
    if not isinstance(stream_id, str) or not stream_id:
        raise InvalidStreamInput("Stream ID must be a nonempty string")
    return stream_id
