"""Replaceable record storage with an in-process implementation."""

from contextlib import AbstractContextManager
from threading import Lock
from typing import Protocol

from .models import Collection, Program


class Store(Protocol):
    """Call record operations inside a transaction."""

    def transaction(self) -> AbstractContextManager[object]: ...

    def get_program(self, program_id: str) -> Program | None: ...

    def list_programs(self) -> tuple[Program, ...]: ...

    def save_program(self, program: Program) -> None: ...

    def remove_program(self, program_id: str) -> None: ...

    def get_collection(self, collection_id: str) -> Collection | None: ...

    def list_collections(self) -> tuple[Collection, ...]: ...

    def save_collection(self, collection: Collection) -> None: ...

    def remove_collection(self, collection_id: str) -> None: ...

    def record_count(self) -> int: ...


class MemoryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._programs: dict[str, Program] = {}
        self._collections: dict[str, Collection] = {}

    def transaction(self) -> AbstractContextManager[bool]:
        return self._lock

    def get_program(self, program_id: str) -> Program | None:
        return self._programs.get(program_id)

    def list_programs(self) -> tuple[Program, ...]:
        return tuple(self._programs.values())

    def save_program(self, program: Program) -> None:
        self._programs[program.id] = program

    def remove_program(self, program_id: str) -> None:
        del self._programs[program_id]

    def get_collection(self, collection_id: str) -> Collection | None:
        return self._collections.get(collection_id)

    def list_collections(self) -> tuple[Collection, ...]:
        return tuple(self._collections.values())

    def save_collection(self, collection: Collection) -> None:
        self._collections[collection.id] = collection

    def remove_collection(self, collection_id: str) -> None:
        del self._collections[collection_id]

    def record_count(self) -> int:
        cases = sum(len(collection.cases) for collection in self._collections.values())
        return len(self._programs) + len(self._collections) + cases
