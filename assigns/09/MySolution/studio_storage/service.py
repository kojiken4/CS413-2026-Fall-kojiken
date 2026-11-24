"""Storage operations and atomic revision checks."""

import re
from collections.abc import Iterable
from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from .errors import ApiError, invalid_request
from .models import Case, CaseWrite, Collection, CollectionWrite, Program, ProgramWrite
from .pagination import Paginator
from .store import Store
from .validation import MAX_PAGE_SIZE

MAX_RECORDS = 500
MAX_CASES_PER_COLLECTION = 50


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


def _require_unique_name(
    records: Iterable[Program | Collection | Case],
    name: str,
    resource: str,
    *,
    excluding: str | None = None,
) -> None:
    if any(record.name == name and record.id != excluding for record in records):
        raise ApiError(409, "duplicate_name", f"A {resource} with that name already exists.")


class StorageService:
    def __init__(self, store: Store) -> None:
        self._store = store
        self._program_pages = Paginator[Program]()
        self._collection_pages = Paginator[Collection]()

    def list_programs(self, limit: int | None, cursor: str | None) -> tuple[tuple[Program, ...], str | None]:
        with self._store.transaction():
            if cursor is not None:
                return self._program_pages.continue_page(cursor, limit)
            return self._program_pages.first_page(self._store.list_programs(), limit or MAX_PAGE_SIZE)

    def create_program(self, fields: ProgramWrite) -> Program:
        with self._store.transaction():
            _require_unique_name(self._store.list_programs(), fields.name, "program")
            self._require_record_space()
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
            _require_unique_name(self._store.list_programs(), fields.name, "program", excluding=program_id)
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

    def list_collections(
        self, limit: int | None, cursor: str | None
    ) -> tuple[tuple[Collection, ...], str | None]:
        with self._store.transaction():
            if cursor is not None:
                return self._collection_pages.continue_page(cursor, limit)
            return self._collection_pages.first_page(self._store.list_collections(), limit or MAX_PAGE_SIZE)

    def create_collection(self, fields: CollectionWrite) -> Collection:
        with self._store.transaction():
            _require_unique_name(self._store.list_collections(), fields.name, "collection")
            self._require_record_space()
            now = utc_timestamp()
            collection = Collection(uuid4().hex, fields.name, fields.description, now, now, 1)
            self._store.save_collection(collection)
            return collection

    def get_collection(self, collection_id: str) -> Collection:
        with self._store.transaction():
            return self._find_collection(collection_id)

    def check_collection_revision(self, collection_id: str, if_match: str | None) -> None:
        with self._store.transaction():
            self._find_collection_at_revision(collection_id, if_match)

    def update_collection(
        self, collection_id: str, if_match: str | None, fields: CollectionWrite
    ) -> Collection:
        with self._store.transaction():
            collection = self._find_collection_at_revision(collection_id, if_match)
            _require_unique_name(
                self._store.list_collections(), fields.name, "collection", excluding=collection_id,
            )
            updated = replace(
                collection,
                name=fields.name,
                description=fields.description,
                updated_at=utc_timestamp(),
                revision=collection.revision + 1,
            )
            self._store.save_collection(updated)
            return updated

    def delete_collection(self, collection_id: str, if_match: str | None) -> None:
        with self._store.transaction():
            self._find_collection_at_revision(collection_id, if_match)
            self._store.remove_collection(collection_id)

    def append_case(self, collection_id: str, if_match: str | None, fields: CaseWrite) -> Collection:
        with self._store.transaction():
            collection = self._find_collection_at_revision(collection_id, if_match)
            _require_unique_name(collection.cases, fields.name, "case")
            if len(collection.cases) >= MAX_CASES_PER_COLLECTION:
                raise ApiError(
                    409, "capacity_limit", f"A collection can hold at most {MAX_CASES_PER_COLLECTION} cases.",
                )
            self._require_record_space()
            case = Case(uuid4().hex, fields.name, fields.source, fields.expected, fields.description)
            return self._replace_cases(collection, (*collection.cases, case))

    def check_case_revision(self, collection_id: str, case_id: str, if_match: str | None) -> None:
        with self._store.transaction():
            self._find_case_at_revision(collection_id, case_id, if_match)

    def update_case(
        self, collection_id: str, case_id: str, if_match: str | None, fields: CaseWrite
    ) -> Collection:
        with self._store.transaction():
            collection, index = self._find_case_at_revision(collection_id, case_id, if_match)
            _require_unique_name(collection.cases, fields.name, "case", excluding=case_id)
            case = Case(case_id, fields.name, fields.source, fields.expected, fields.description)
            cases = collection.cases[:index] + (case,) + collection.cases[index + 1:]
            return self._replace_cases(collection, cases)

    def delete_case(self, collection_id: str, case_id: str, if_match: str | None) -> Collection:
        with self._store.transaction():
            collection, index = self._find_case_at_revision(collection_id, case_id, if_match)
            cases = collection.cases[:index] + collection.cases[index + 1:]
            return self._replace_cases(collection, cases)

    def _find_collection(self, collection_id: str) -> Collection:
        collection = self._store.get_collection(collection_id)
        if collection is None:
            raise ApiError(404, "record_not_found", "Collection not found.")
        return collection

    def _find_collection_at_revision(self, collection_id: str, if_match: str | None) -> Collection:
        collection = self._find_collection(collection_id)
        require_revision(if_match, collection.revision)
        return collection

    def _find_case_at_revision(
        self, collection_id: str, case_id: str, if_match: str | None
    ) -> tuple[Collection, int]:
        collection = self._find_collection(collection_id)
        for index, case in enumerate(collection.cases):
            if case.id == case_id:
                require_revision(if_match, collection.revision)
                return collection, index
        raise ApiError(404, "record_not_found", "Case not found in this collection.")

    def _replace_cases(self, collection: Collection, cases: tuple[Case, ...]) -> Collection:
        updated = replace(
            collection, cases=cases, updated_at=utc_timestamp(), revision=collection.revision + 1,
        )
        self._store.save_collection(updated)
        return updated

    def _require_record_space(self) -> None:
        if self._store.record_count() >= MAX_RECORDS:
            raise ApiError(
                409, "capacity_limit", f"The live store can hold at most {MAX_RECORDS} records.",
            )
