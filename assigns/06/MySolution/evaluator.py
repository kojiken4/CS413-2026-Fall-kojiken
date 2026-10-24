"""Shared evaluation engine, initially supporting bounded pure target execution.

Source cases will extend this same loop in Step 4. Target execution uses only
target syntax and capture-avoiding substitution; there are no encoding shortcuts.
"""

from dataclasses import dataclass
from typing import Literal

from .target import App, Lam, Term, Var, free_vars, substitute


class OpenTermError(ValueError):
    """Execution requires a closed target term; structural operations do not."""


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    status: Literal["completed", "exhausted"]
    term: Term
    steps: int
    budget: int

    @property
    def value(self) -> Lam | None:
        """Expose a value only after successful completion."""
        if self.status == "completed" and isinstance(self.term, Lam):
            return self.term
        return None


@dataclass(frozen=True, slots=True)
class _EvaluateArgument:
    """The function is being evaluated; its argument must wait."""
    arg: Term


@dataclass(frozen=True, slots=True)
class _Apply:
    """The function is a value; wait for its argument before applying it."""
    fn: Lam


type _Frame = _EvaluateArgument | _Apply


def _rebuild_term(current: Term, frames: list[_Frame]) -> Term:
    """Put an unfinished expression back into its surrounding applications."""
    for frame in reversed(frames):
        match frame:
            case _EvaluateArgument(arg):
                current = App(current, arg)
            case _Apply(fn):
                current = App(fn, current)
    return current


def evaluate(expression: Term, *, max_steps: int) -> EvaluationResult:
    """Run closed target syntax by weak, left-to-right call-by-value.

    Count only beta-value contractions, not traversal or bookkeeping. Budgets
    must be nonnegative integers (booleans are rejected). Exhaustion returns the
    complete residual term after exactly the allowed number of contractions.
    """
    if isinstance(max_steps, bool) or not isinstance(max_steps, int):
        raise TypeError("max_steps must be a nonnegative integer")
    if max_steps < 0:
        raise ValueError("max_steps must be nonnegative")

    if not isinstance(expression, (Var, Lam, App)):
        raise TypeError("expected a target Var, Lam, or App")
    free = free_vars(expression)
    if free:
        raise OpenTermError(
            "target execution requires a closed term; free variables: "
            + ", ".join(sorted(free))
        )

    current = expression
    frames: list[_Frame] = []
    steps = 0

    while True:
        match current:
            case App(fn, arg):
                frames.append(_EvaluateArgument(arg))
                current = fn
            case Lam():
                if not frames:
                    return EvaluationResult("completed", current, steps, max_steps)

                frame = frames.pop()
                match frame:
                    case _EvaluateArgument(arg):
                        frames.append(_Apply(current))
                        current = arg
                    case _Apply(fn):
                        # Both operands are lambda values. Check before contracting.
                        if steps == max_steps:
                            residual = _rebuild_term(App(fn, current), frames)
                            return EvaluationResult("exhausted", residual, steps, max_steps)
                        current = substitute(fn.body, fn.name, current)
                        steps += 1
            case Var(name):
                # Unreachable for valid closed inputs and capture-avoiding steps.
                raise OpenTermError(f"cannot execute unbound target variable: {name}")
            case _:
                raise TypeError("expected a target Var, Lam, or App")
