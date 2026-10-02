"""Run real language operations in disposable workers with a time limit."""

import json
import math
from pathlib import Path
import subprocess
import sys

from .backend import LambdaBackend
from .contracts import Operation, OperationResult, Outcome
from .source_validation import SourceValidationError, validate_source
from .worker_protocol import decode_result

DEFAULT_TIMEOUT_SECONDS = 5.0
_PACKAGE_ROOT = Path(__file__).resolve().parent.parent


class BoundedBackend(LambdaBackend):
    """Synchronous backend protocol; async callers must use asyncio.to_thread.

    Lint/Interpret run in fresh subprocesses. Placeholder/Execute methods are
    inherited unchanged; this never executes user-selected programs or a shell.
    """

    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        if (
            type(timeout_seconds) not in (int, float)
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValueError("Timeout must be a positive finite number of seconds.")
        self.timeout_seconds = float(timeout_seconds)

    def lint(self, source: str, source_revision: int) -> OperationResult:
        return self._run_worker(Operation.LINT, source, source_revision)

    def interpret(self, source: str, source_revision: int) -> OperationResult:
        return self._run_worker(Operation.INTERPRET, source, source_revision)

    def _run_worker(
        self, operation: Operation, source: str, source_revision: int
    ) -> OperationResult:
        try:
            validate_source(source)
        except SourceValidationError as error:
            return OperationResult(operation, source_revision, Outcome.INVALID_INPUT, str(error))
        try:
            payload = json.dumps({
                "operation": operation.value,
                "source": source,
                "source_revision": source_revision,
            }).encode("utf-8")
            # run() kills and waits for the child on timeout and closes its pipes.
            completed = subprocess.run(
                [sys.executable, "-m", "lambda_web.worker"],
                input=payload, capture_output=True, shell=False,
                cwd=_PACKAGE_ROOT, timeout=self.timeout_seconds,
            )
            if completed.returncode != 0:
                diagnostic = completed.stderr.decode("utf-8", errors="replace").strip()
                return OperationResult(
                    operation, source_revision, Outcome.BACKEND_FAILURE,
                    f"Worker exited with code {completed.returncode}. {diagnostic}",
                )
            return decode_result(completed.stdout.decode("utf-8"), operation, source_revision)
        except subprocess.TimeoutExpired:
            return OperationResult(
                operation, source_revision, Outcome.BACKEND_FAILURE,
                f"Language operation timed out after {self.timeout_seconds:g} seconds "
                "(including worker startup and parsing). The worker was stopped.",
            )
        except Exception as error:
            return OperationResult(
                operation, source_revision, Outcome.BACKEND_FAILURE,
                f"Worker failure ({type(error).__name__}): {error}",
            )
