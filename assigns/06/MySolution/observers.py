"""Read encoded data by bounded pure-target contexts in the shared evaluator.

Python inspects only the final marker or spine shape. It does not execute
generated arithmetic or reduce beneath lambdas. Pair support follows in Step 6.
"""

from dataclasses import dataclass
from typing import Literal

from .encodings import boolean, identity
from .evaluator import evaluate
from .target import (
    App, FreshNameGenerator, Lam, Term, Var, all_names, alpha_equivalent,
)


type ExpectedKind = Literal["natural", "boolean"]


@dataclass(frozen=True, slots=True)
class ObservationResult:
    status: Literal["completed", "exhausted", "malformed"]
    value: int | bool | None
    term: Term
    steps: int
    budget: int
    diagnostic: str | None = None


class _MalformedShape(ValueError):
    """A completed observation did not yield the documented output shape."""


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


def observe(value: Lam, expected_kind: ExpectedKind, *, max_steps: int) -> ObservationResult:
    """Observe a completed closed target lambda using a separate step budget.

    Invalid API arguments raise errors; a completed context with an unrecognized
    output shape returns 'malformed'. Exhaustion never exposes a decoded value.
    """
    if expected_kind not in ("natural", "boolean"):
        raise ValueError("expected_kind must be 'natural' or 'boolean'")
    if not isinstance(value, Lam):
        raise TypeError("observation requires a completed target lambda value")

    names = FreshNameGenerator(all_names(value))
    if expected_kind == "natural":
        context = _natural_context(value, names)
    else:
        # Distinct closed values: I and FALSE. These are markers, not primitives.
        true_marker = identity(names=names)
        false_marker = boolean(False, names=names)
        context = App(App(value, true_marker), false_marker)

    execution = evaluate(context, max_steps=max_steps)
    if execution.status == "exhausted":
        return ObservationResult(
            "exhausted", None, execution.term, execution.steps, max_steps,
            "observation step budget exhausted",
        )

    try:
        if expected_kind == "natural":
            decoded = _count_spine(execution.term)
        elif alpha_equivalent(execution.term, true_marker):
            decoded = True
        elif alpha_equivalent(execution.term, false_marker):
            decoded = False
        else:
            raise _MalformedShape("boolean observation did not select either marker")
    except _MalformedShape as error:
        return ObservationResult(
            "malformed", None, execution.term, execution.steps, max_steps, str(error),
        )

    return ObservationResult("completed", decoded, execution.term, execution.steps, max_steps)
