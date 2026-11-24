"""Write fields and immutable stored records."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ProgramWrite:
    name: str
    source: str
    description: str


@dataclass(frozen=True, slots=True)
class Program:
    id: str
    name: str
    source: str
    description: str
    created_at: str
    updated_at: str
    revision: int

    def to_dict(self) -> dict[str, str | int]:
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revision": self.revision,
        }


@dataclass(frozen=True, slots=True)
class ValueExpectation:
    value: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": "value", "value": self.value}


@dataclass(frozen=True, slots=True)
class ErrorExpectation:
    category: Literal["syntax", "type"]

    def to_dict(self) -> dict[str, str]:
        return {"kind": "error", "category": self.category}


type ExpectedOutcome = ValueExpectation | ErrorExpectation


@dataclass(frozen=True, slots=True)
class CaseWrite:
    name: str
    source: str
    expected: ExpectedOutcome
    description: str


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    name: str
    source: str
    expected: ExpectedOutcome
    description: str

    def to_dict(self) -> dict[str, str | dict[str, str]]:
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "expected": self.expected.to_dict(),
            "description": self.description,
        }


@dataclass(frozen=True, slots=True)
class CollectionWrite:
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class Collection:
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    revision: int
    cases: tuple[Case, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revision": self.revision,
            "cases": [case.to_dict() for case in self.cases],
        }
