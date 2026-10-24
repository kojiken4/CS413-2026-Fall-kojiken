"""Read encoded data by bounded pure-target contexts in the shared evaluator.

Python inspects only the final marker or spine shape. It does not execute
generated arithmetic or reduce beneath lambdas. Nested pair projections and
scalar contexts all consume one observation budget per public call.
"""

from dataclasses import dataclass
from typing import Literal

from .encodings import boolean, first, identity, second
from .evaluator import evaluate
from .target import (
    App, FreshNameGenerator, Lam, Term, Var, all_names, alpha_equivalent,
)


type ExpectedKind = (
    Literal["natural", "boolean"] | tuple[Literal["pair"], ExpectedKind, ExpectedKind]
)
type DecodedValue = int | bool | tuple[DecodedValue, DecodedValue]


@dataclass(frozen=True, slots=True)
class ObservationResult:
    status: Literal["completed", "exhausted", "malformed"]
    value: DecodedValue | None
    term: Term
    steps: int
    budget: int
    diagnostic: str | None = None


class _MalformedShape(ValueError):
    """A completed observation did not yield the documented output shape."""


class _ObservationFailure(Exception):
    def __init__(self, status: str, term: Term, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.status = status
        self.term = term


@dataclass(slots=True)
class _Budget:
    """Local mutable accounting; no target terms are mutated."""
    limit: int
    steps: int
    term: Term

    def run(self, context: Term, path: str) -> Lam:
        execution = evaluate(context, max_steps=self.limit - self.steps)
        self.steps += execution.steps
        self.term = execution.term
        if execution.status == "exhausted":
            raise _ObservationFailure(
                "exhausted", self.term, f"observation step budget exhausted at {path}",
            )
        return execution.value


def _validate_kind(kind: ExpectedKind) -> None:
    if kind in ("natural", "boolean"):
        return
    if isinstance(kind, tuple) and len(kind) == 3 and kind[0] == "pair":
        _validate_kind(kind[1])
        _validate_kind(kind[2])
        return
    raise ValueError(
        "expected_kind must be 'natural', 'boolean', or ('pair', left_kind, right_kind)"
    )


def _natural_context(value: Lam, names: FreshNameGenerator) -> Term:
    # STEP = lam tail. lam c. lam z. c tail
    tail, choice, zero = names.fresh("tail"), names.fresh("c"), names.fresh("z")
    step = Lam(tail, Lam(choice, Lam(zero, App(Var(choice), Var(tail)))))
    # BASE = lam c. lam z. z
    base_choice, base_zero = names.fresh("c"), names.fresh("z")
    base = Lam(base_choice, Lam(base_zero, Var(base_zero)))
    return App(App(value, step), base)


def _count_spine(term: Term) -> int:
    """Inspect BASE or NODE(tail) shapes, accounting for local binder scope."""
    count = 0
    current = term
    while True:
        match current:
            case Lam(choice, Lam(zero, Var(name))) if name == zero:
                return count
            case Lam(choice, Lam(zero, App(Var(name), tail))) if (
                name == choice and choice != zero
            ):
                count += 1
                current = tail
            case _:
                raise _MalformedShape("natural observation did not produce a finite spine")


def _observe(value: Lam, kind: ExpectedKind, budget: _Budget, path: str) -> DecodedValue:
    names = FreshNameGenerator(all_names(value))
    if isinstance(kind, tuple):
        left_value = budget.run(App(first(names=names), value), path + ".first.projection")
        left = _observe(left_value, kind[1], budget, path + ".first")
        right_value = budget.run(App(second(names=names), value), path + ".second.projection")
        right = _observe(right_value, kind[2], budget, path + ".second")
        return left, right

    if kind == "natural":
        context = _natural_context(value, names)
    else:
        # Distinct closed values: I and FALSE. These are markers, not primitives.
        true_marker = identity(names=names)
        false_marker = boolean(False, names=names)
        context = App(App(value, true_marker), false_marker)

    output = budget.run(context, path)

    try:
        if kind == "natural":
            return _count_spine(output)
        elif alpha_equivalent(output, true_marker):
            return True
        elif alpha_equivalent(output, false_marker):
            return False
        else:
            raise _MalformedShape("boolean observation did not select either marker")
    except _MalformedShape as error:
        raise _ObservationFailure("malformed", output, f"{path}: {error}") from error


def observe(value: Lam, expected_kind: ExpectedKind, *, max_steps: int) -> ObservationResult:
    """Observe a completed closed target value with one aggregate observation cap.

    Pair kinds are ('pair', left_kind, right_kind), recursively. Components are
    projected and observed depth-first, left before right. Failure discards any
    partial decoded tuple and reports the failing context and its data path.
    """
    _validate_kind(expected_kind)
    if not isinstance(value, Lam):
        raise TypeError("observation requires a completed target lambda value")
    if isinstance(max_steps, bool) or not isinstance(max_steps, int):
        raise TypeError("max_steps must be a nonnegative integer")
    if max_steps < 0:
        raise ValueError("max_steps must be nonnegative")

    budget = _Budget(max_steps, 0, value)
    try:
        decoded = _observe(value, expected_kind, budget, "result")
    except _ObservationFailure as failure:
        return ObservationResult(
            failure.status, None, failure.term, budget.steps, max_steps, str(failure),
        )
    # A pair has multiple observation contexts, so no single final context term.
    output = value if isinstance(expected_kind, tuple) else budget.term
    return ObservationResult("completed", decoded, output, budget.steps, max_steps)
