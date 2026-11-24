"""Program operations and atomic revision checks."""

import re
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from .errors import ApiError, invalid_request
from .models import Program, ProgramWrite
from .pagination import Paginator
from .store import Store
from .validation import MAX_PAGE_SIZE

MAX_RECORDS = 500


def revision_tag(revision: int) -> str:
    return f'"{revision}"'


def require_revision(if_match: str | None, revision: int) -> None:
    if if_match is None:
        raise ApiError(428, "precondition_required", "Send the current ETag in If-Match.")
    if re.fullmatch(r'"[1-9][0-9]*"', if_match) is None:
        raise invalid_request("If-Match must be one quoted positive decimal revision.")
    if if_match != revision_tag(revision):
        raise ApiError(
            409, "revision_conflict", "If-Match does not match the current revision.",
            current_revision=revision,
        )


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class StorageService:
    def __init__(self, store: Store) -> None:
        self._store = store
        self._program_pages = Paginator[Program]()

    def list_programs(self, limit: int | None, cursor: str | None) -> tuple[tuple[Program, ...], str | None]:
        with self._store.transaction():
            if cursor is not None:
                return self._program_pages.continue_page(cursor, limit)
            return self._program_pages.first_page(self._store.list_programs(), limit or MAX_PAGE_SIZE)

    def create_program(self, fields: ProgramWrite) -> Program:
        with self._store.transaction():
            self._require_unique_program_name(fields.name)
            if self._store.record_count() >= MAX_RECORDS:
                raise ApiError(409, "capacity_limit", f"The live store can hold at most {MAX_RECORDS} records.")
            now = utc_timestamp()
            program = Program(uuid4().hex, fields.name, fields.source, fields.description, now, now, 1)
            self._store.save_program(program)
            return program

    def get_program(self, program_id: str) -> Program:
        with self._store.transaction():
            return self._find_program(program_id)

    def check_program_revision(self, program_id: str, if_match: str | None) -> None:
        with self._store.transaction():
            self._find_program_at_revision(program_id, if_match)

    def update_program(self, program_id: str, if_match: str | None, fields: ProgramWrite) -> Program:
        with self._store.transaction():
            program = self._find_program_at_revision(program_id, if_match)
            self._require_unique_program_name(fields.name, excluding=program_id)
            updated = replace(
                program,
                name=fields.name,
                source=fields.source,
                description=fields.description,
                updated_at=utc_timestamp(),
                revision=program.revision + 1,
            )
            self._store.save_program(updated)
            return updated

    def delete_program(self, program_id: str, if_match: str | None) -> None:
        with self._store.transaction():
            self._find_program_at_revision(program_id, if_match)
            self._store.remove_program(program_id)

    def _find_program_at_revision(self, program_id: str, if_match: str | None) -> Program:
        program = self._find_program(program_id)
        require_revision(if_match, program.revision)
        return program

    def _find_program(self, program_id: str) -> Program:
        program = self._store.get_program(program_id)
        if program is None:
            raise ApiError(404, "record_not_found", "Program not found.")
        return program

    def _require_unique_program_name(self, name: str, *, excluding: str | None = None) -> None:
        if any(program.name == name and program.id != excluding for program in self._store.list_programs()):
            raise ApiError(409, "duplicate_name", "A program with that name already exists.")
