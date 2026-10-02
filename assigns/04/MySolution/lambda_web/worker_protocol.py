"""Internal JSON result transport; never deserialize executable Python objects."""

import json

from .contracts import Operation, OperationResult, Outcome


class WorkerProtocolError(ValueError):
    """A worker response does not match the operation contract."""


def encode_result(result: OperationResult) -> str:
    if result.artifact is not None:
        raise WorkerProtocolError("Generated artifacts are not supported.")
    return json.dumps({
        "operation": result.operation.value,
        "source_revision": result.source_revision,
        "outcome": result.outcome.value,
        "output": result.output,
        "free_variables": sorted(result.free_variables) if result.free_variables is not None else None,
        "artifact": None,
    })


def decode_result(payload: str, operation: Operation, revision: int) -> OperationResult:
    try:
        data = json.loads(payload)
        if not isinstance(data, dict) or set(data) != {
            "operation", "source_revision", "outcome", "output", "free_variables", "artifact",
        }:
            raise WorkerProtocolError("Unexpected result fields.")
        if data["operation"] != operation.value:
            raise WorkerProtocolError("Worker returned a different operation.")
        if type(data["source_revision"]) is not int or data["source_revision"] != revision:
            raise WorkerProtocolError("Worker returned a different source revision.")
        if not isinstance(data["output"], str) or data["artifact"] is not None:
            raise WorkerProtocolError("Invalid output or unsupported artifact.")
        variables = data["free_variables"]
        if variables is not None and (
            not isinstance(variables, list) or any(not isinstance(name, str) for name in variables)
        ):
            raise WorkerProtocolError("Invalid free-variable result.")
        return OperationResult(
            operation, revision, Outcome(data["outcome"]), data["output"],
            free_variables=frozenset(variables) if variables is not None else None,
        )
    except (ValueError, TypeError) as error:
        raise WorkerProtocolError(f"Invalid worker response: {error}") from error
