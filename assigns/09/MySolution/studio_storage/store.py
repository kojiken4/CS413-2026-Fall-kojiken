"""Replaceable record storage with an in-process implementation."""

from contextlib import AbstractContextManager
from threading import Lock
from typing import Protocol

from .models import Program


class Store(Protocol):
    """Call record operations inside a transaction."""

    def transaction(self) -> AbstractContextManager[object]: ...

    def get_program(self, program_id: str) -> Program | None: ...

    def list_programs(self) -> tuple[Program, ...]: ...

    def save_program(self, program: Program) -> None: ...

    def remove_program(self, program_id: str) -> None: ...

    def record_count(self) -> int: ...


class MemoryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._programs: dict[str, Program] = {}

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

    def record_count(self) -> int:
        return len(self._programs)
