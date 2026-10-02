"""Framework-independent contracts shared by the model and language adapter."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class Operation(StrEnum):
    LINT = "lint"
    INTERPRET = "interpret"
    TYPECHECK = "typecheck"
    COMPILE = "compile"
    EXECUTE = "execute"


class Outcome(StrEnum):
    SUCCESS = "success"
    INVALID_INPUT = "invalid_input"
    LANGUAGE_ERROR = "language_error"
    RUNTIME_ERROR = "runtime_error"
    BACKEND_FAILURE = "backend_failure"
    NOT_IMPLEMENTED = "not_implemented"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class GeneratedArtifact:
    """Future compiler output; never created by the current adapter."""

    source_revision: int
    code: str
    code_format: str


@dataclass(frozen=True)
class OperationResult:
    operation: Operation
    source_revision: int
    outcome: Outcome
    output: str
    free_variables: frozenset[str] | None = None
    artifact: GeneratedArtifact | None = None


class LanguageBackend(Protocol):
    """Replaceable tools; model/controller enforce source state prerequisites."""

    def lint(self, source: str, source_revision: int) -> OperationResult: ...

    def interpret(self, source: str, source_revision: int) -> OperationResult: ...

    def typecheck(self, source: str, source_revision: int) -> OperationResult: ...

    def compile(self, source: str, source_revision: int) -> OperationResult: ...

    def execute(
        self, artifact: GeneratedArtifact | None, source_revision: int
    ) -> OperationResult: ...
