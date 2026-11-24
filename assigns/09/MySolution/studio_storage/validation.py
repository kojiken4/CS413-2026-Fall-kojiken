"""Validate API inputs before constructing write fields."""

from collections.abc import Mapping, Sequence

from .errors import invalid_request
from .models import (
    CaseWrite, CollectionWrite, ErrorExpectation, ExpectedOutcome, ProgramWrite, ValueExpectation,
)

MAX_SOURCE_BYTES = 16_384
MAX_DESCRIPTION_LENGTH = 2_048
MAX_PAGE_SIZE = 50


def program_write(payload: object) -> ProgramWrite:
    fields = _write_object(payload, {"name", "source", "description"})
    return ProgramWrite(_name(fields), _source(fields), _description(fields))


def collection_write(payload: object) -> CollectionWrite:
    fields = _write_object(payload, {"name", "description"})
    return CollectionWrite(_name(fields), _description(fields))


def case_write(payload: object) -> CaseWrite:
    fields = _write_object(payload, {"name", "source", "expected", "description"})
    return CaseWrite(_name(fields), _source(fields), _expected(fields.get("expected")), _description(fields))


def _write_object(payload: object, allowed: set[str]) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise invalid_request("The request body must be a JSON object.")
    if payload.keys() - allowed:
        raise invalid_request("The request body contains an unknown field.")
    return payload


def _name(fields: dict[str, object]) -> str:
    return _text_field(fields.get("name"), "name", nonblank=True).strip()


def _source(fields: dict[str, object]) -> str:
    source = _text_field(fields.get("source"), "source", nonblank=True)
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise invalid_request(f"source must be at most {MAX_SOURCE_BYTES} UTF-8 bytes.")
    return source


def _description(fields: dict[str, object]) -> str:
    description = _text_field(fields.get("description", ""), "description")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise invalid_request(f"description must be at most {MAX_DESCRIPTION_LENGTH} characters.")
    return description


def _expected(value: object) -> ExpectedOutcome:
    if isinstance(value, dict) and len(value) == 2:
        match value:
            case {"kind": "value", "value": formatted}:
                return ValueExpectation(_text_field(formatted, "expected.value"))
            case {"kind": "error", "category": ("syntax" | "type") as category}:
                return ErrorExpectation(category)
    raise invalid_request("expected must contain kind and a formatted value or syntax/type error category.")


def _text_field(value: object, field: str, *, nonblank: bool = False) -> str:
    if not isinstance(value, str) or (nonblank and not value.strip()):
        qualifier = "nonblank " if nonblank else ""
        raise invalid_request(f"{field} must be a {qualifier}string.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise invalid_request(f"{field} must contain valid Unicode text.") from None
    return value


def record_id(value: str) -> str:
    if not value or "/" in value or "\x00" in value:
        raise invalid_request("The record ID must be a single nonempty path segment.")
    return value


def page_parameters(parameters: Mapping[str, Sequence[str]]) -> tuple[int | None, str | None]:
    if parameters.keys() - {"limit", "cursor"} or any(len(values) != 1 for values in parameters.values()):
        raise invalid_request("Use only limit and cursor, each at most once.")
    limit = None
    if "limit" in parameters:
        raw_limit = parameters["limit"][0]
        digits = raw_limit.lstrip("0")
        if not digits.isascii() or not digits.isdecimal() or len(digits) > len(str(MAX_PAGE_SIZE)):
            raise invalid_request(f"limit must be an integer from 1 to {MAX_PAGE_SIZE}.")
        limit = int(digits)
        if limit > MAX_PAGE_SIZE:
            raise invalid_request(f"limit must be an integer from 1 to {MAX_PAGE_SIZE}.")
    cursor = parameters["cursor"][0] if "cursor" in parameters else None
    if cursor == "":
        raise invalid_request("cursor must be a nonempty token returned by the service.")
    return limit, cursor
