"""Adapt the supplied LAMBDA language tools to revision-associated results.

This is the in-process language implementation used inside bounded workers.
It is independent of HTTP, browser rendering, and application state.
"""

from . import lambda1
from .constructor_reader import ConstructorInputError, read_constructor
from .contracts import GeneratedArtifact, Operation, OperationResult, Outcome


class LambdaBackend:
    def lint(self, source: str, source_revision: int) -> OperationResult:
        return self._process(Operation.LINT, source, source_revision)

    def interpret(self, source: str, source_revision: int) -> OperationResult:
        return self._process(Operation.INTERPRET, source, source_revision)

    def typecheck(self, source: str, source_revision: int) -> OperationResult:
        return OperationResult(
            Operation.TYPECHECK, source_revision, Outcome.NOT_IMPLEMENTED,
            "Type checking is not yet implemented.",
        )

    def compile(self, source: str, source_revision: int) -> OperationResult:
        return OperationResult(
            Operation.COMPILE, source_revision, Outcome.NOT_IMPLEMENTED,
            "Compilation is not yet implemented.",
        )

    def execute(
        self, artifact: GeneratedArtifact | None, source_revision: int
    ) -> OperationResult:
        return OperationResult(
            Operation.EXECUTE, source_revision, Outcome.UNAVAILABLE,
            "Execute is for generated code and is unavailable until compilation "
            "is implemented and produces an artifact. Generated-code execution "
            "is not implemented.",
        )

    def _process(
        self, operation: Operation, source: str, source_revision: int
    ) -> OperationResult:
        try:
            try:
                expression = read_constructor(source)
            except ConstructorInputError as error:
                return OperationResult(
                    operation, source_revision, Outcome.INVALID_INPUT, str(error),
                )
            if operation is Operation.LINT:
                variables = lambda1.d0exp_fvset(expression)
                if not isinstance(variables, frozenset) or any(
                    not isinstance(name, str) for name in variables
                ):
                    raise RuntimeError("Free-variable tool returned an invalid result.")
                return OperationResult(
                    operation, source_revision,
                    Outcome.LANGUAGE_ERROR if variables else Outcome.SUCCESS,
                    "Undeclared variables: " + ", ".join(repr(name) for name in sorted(variables))
                    if variables else "No free variables were found.",
                    free_variables=variables,
                )
            try:
                value = lambda1.d0exp_evaluate(expression, lambda1.ENVnil())
            except (ArithmeticError, TypeError, ValueError, RecursionError) as error:
                return OperationResult(
                    operation, source_revision, Outcome.RUNTIME_ERROR,
                    f"{type(error).__name__}: {error}",
                )
            if not isinstance(value, lambda1.D0V000):
                raise RuntimeError("Interpreter returned an invalid value.")
            if _contains_error_sentinel(value):
                return OperationResult(
                    operation, source_revision, Outcome.RUNTIME_ERROR,
                    "Evaluation returned D0V000() (an unresolved variable) "
                    "directly or inside a pair.",
                )
            return OperationResult(operation, source_revision, Outcome.SUCCESS, str(value))
        except Exception as error:
            # Unexpected tool/adapter failures are distinct from user diagnostics.
            return OperationResult(
                operation, source_revision, Outcome.BACKEND_FAILURE,
                f"Backend failure ({type(error).__name__}): {error}",
            )


def _contains_error_sentinel(value: lambda1.d0val) -> bool:
    pending = [value]
    while pending:
        current = pending.pop()
        # Every successful value also subclasses D0V000: isinstance is wrong here.
        if type(current) is lambda1.D0V000:
            return True
        if isinstance(current, lambda1.D0Vpair):
            pending.extend((current.arg1, current.arg2))
    return False
