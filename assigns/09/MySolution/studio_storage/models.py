"""Program fields and immutable stored records."""

from dataclasses import dataclass


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
