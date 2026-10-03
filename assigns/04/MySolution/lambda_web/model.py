"""Framework-independent application state and guarded MVC transitions.

No language tools, files, browser elements, or HTTP objects are accessed here.
Mutations are atomic under a short-lived lock; backend work happens outside it.
"""

from dataclasses import dataclass, replace
from threading import RLock

from .contracts import GeneratedArtifact, Operation, OperationResult
from .source_validation import SourceValidationError, validate_source


class ModelStateError(ValueError):
    """An action conflicts with the application's current state."""


@dataclass(frozen=True)
class ApplicationState:
    applied_source: str | None = None
    source_name: str | None = None
    draft: str = ""
    draft_name: str = "Manual input"
    revision: int = 0
    results: tuple[OperationResult, ...] = ()
    artifact: GeneratedArtifact | None = None
    active_operation: Operation | None = None

    @property
    def dirty(self) -> bool:
        return self.draft != (self.applied_source or "")

    @property
    def busy(self) -> bool:
        return self.active_operation is not None

    def can_run(self, operation: Operation) -> bool:
        # This version has no compiler or generated-code executor.
        return (
            isinstance(operation, Operation)
            and operation is not Operation.EXECUTE
            and self.applied_source is not None
            and not self.dirty
            and not self.busy
        )


@dataclass(frozen=True)
class OperationRequest:
    """Capture applied source/revision for one operation, without invoking it."""

    operation: Operation
    source: str
    source_revision: int


class ApplicationModel:
    def __init__(self) -> None:
        self._state = ApplicationState()
        self._active_request: OperationRequest | None = None
        self._lock = RLock()

    @property
    def state(self) -> ApplicationState:
        with self._lock:
            return self._state

    def set_draft(self, source: str) -> None:
        with self._lock:
            self._require_idle()
            if not isinstance(source, str):
                raise SourceValidationError("Draft must be text.")
            # Retain invalid text so rejected edits can be corrected in place.
            self._state = replace(self._state, draft=source)

    def start_manual_input(self) -> None:
        with self._lock:
            self._require_replace_allowed()
            self._state = replace(self._state, draft="", draft_name="Manual input")

    def discard_changes(self) -> None:
        with self._lock:
            self._require_idle()
            self._state = replace(
                self._state, draft=self._state.applied_source or "",
                draft_name=self._state.source_name or "Manual input",
            )

    def apply_changes(self) -> None:
        with self._lock:
            self._require_idle()
            validate_source(self._state.draft)
            if self._state.applied_source is not None and not self._state.dirty:
                raise ModelStateError("There are no unapplied changes.")
            self._accept_source(self._state.draft, self._state.draft_name)

    def load_source(self, source: str, name: str) -> None:
        """Accept decoded uploads/canned inputs; never touch the original file."""
        with self._lock:
            self._require_replace_allowed()
            if not isinstance(name, str) or not name.strip():
                raise SourceValidationError("Source name must be nonempty text.")
            try:
                validate_source(source)
            except SourceValidationError:
                if isinstance(source, str):
                    self._state = replace(self._state, draft=source, draft_name=name)
                raise
            self._accept_source(source, name)

    def check_source_replacement(self) -> None:
        """Check before asynchronous upload work; load_source checks again."""
        with self._lock:
            self._require_replace_allowed()

    def begin_operation(self, operation: Operation) -> OperationRequest:
        with self._lock:
            self._require_replace_allowed()
            if not isinstance(operation, Operation):
                raise ModelStateError("Unknown operation.")
            if self._state.applied_source is None:
                raise ModelStateError("Apply or load source before running an operation.")
            if operation is Operation.EXECUTE:
                raise ModelStateError(
                    "Execute is unavailable because no generated code exists."
                )
            request = OperationRequest(
                operation, self._state.applied_source, self._state.revision,
            )
            self._active_request = request
            self._state = replace(self._state, active_operation=operation)
            return request

    def finish_operation(self, request: OperationRequest, result: OperationResult) -> None:
        """Record a matching result and leave busy state, preserving source.

        Invalid completions leave state unchanged. The controller must call
        abort_operation in cleanup if work cannot produce a valid result.
        """
        with self._lock:
            if self._state.active_operation is None:
                raise ModelStateError("No operation is in progress.")
            if request is not self._active_request:
                raise ModelStateError("Result does not belong to the active request.")
            if not isinstance(result, OperationResult):
                raise ModelStateError("Expected an operation result.")
            if result.operation is not self._state.active_operation:
                raise ModelStateError("Result operation does not match active work.")
            if result.source_revision != self._state.revision:
                raise ModelStateError("Result belongs to a different source revision.")
            if result.artifact is not None:
                raise ModelStateError("Generated artifacts are not supported in this version.")
            self._state = replace(
                self._state, results=self._state.results + (result,),
                active_operation=None, artifact=None,
            )
            self._active_request = None

    def abort_operation(self, request: OperationRequest) -> None:
        """Release only this request's busy state; safe in controller cleanup."""
        with self._lock:
            if self._active_request is request:
                self._state = replace(self._state, active_operation=None)
                self._active_request = None

    def _require_idle(self) -> None:
        if self._state.busy:
            raise ModelStateError("An operation is in progress.")

    def _require_replace_allowed(self) -> None:
        self._require_idle()
        if self._state.dirty:
            raise ModelStateError("Apply or discard changes before continuing.")

    def _accept_source(self, source: str, name: str) -> None:
        self._state = replace(
            self._state, applied_source=source, source_name=name,
            draft=source, draft_name=name, revision=self._state.revision + 1,
            results=(), artifact=None,
        )
