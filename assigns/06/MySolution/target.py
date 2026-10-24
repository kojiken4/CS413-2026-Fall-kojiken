"""Pure target syntax and structural operations; no evaluation occurs here.

The naming and scoped-renaming approach adapts Assignment 5 MySolution/operations.py.
Target terms are separate immutable nodes, and substitution supports open terms.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re


def _validate_name(name: str) -> None:
    if not isinstance(name, str):
        raise TypeError("identifier must be a string")
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
        raise ValueError(f"invalid identifier: {name!r}")


@dataclass(frozen=True, slots=True)
class Var:
    name: str

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True, slots=True)
class Lam:
    name: str
    body: Term

    def __post_init__(self) -> None:
        _validate_name(self.name)


@dataclass(frozen=True, slots=True)
class App:
    fn: Term
    arg: Term


type Term = Var | Lam | App


def pretty(term: Term) -> str:
    """Print the assignment's fully parenthesized single-parameter notation."""
    match term:
        case Var(name):
            return name
        case Lam(name, body):
            return f"(lam {name}. {pretty(body)})"
        case App(fn, arg):
            return f"({pretty(fn)} {pretty(arg)})"
        case _:
            raise TypeError("expected a target Var, Lam, or App")


def free_vars(term: Term) -> frozenset[str]:
    """Return the variable names not bound within this term."""
    match term:
        case Var(name):
            return frozenset({name})
        case Lam(name, body):
            return free_vars(body) - {name}
        case App(fn, arg):
            return free_vars(fn) | free_vars(arg)
        case _:
            raise TypeError("expected a target Var, Lam, or App")


def all_names(term: Term) -> frozenset[str]:
    """Include every variable occurrence and binder, even unused binders."""
    match term:
        case Var(name):
            return frozenset({name})
        case Lam(name, body):
            return all_names(body) | {name}
        case App(fn, arg):
            return all_names(fn) | all_names(arg)
        case _:
            raise TypeError("expected a target Var, Lam, or App")


class FreshNameGenerator:
    """Generate base_counter names, skipping reserved and previously returned names.

    One counter is shared across bases. Each attempted candidate advances it,
    including skipped candidates. The caller's reserved collection is copied.
    """

    def __init__(self, reserved_names: Iterable[str] = ()) -> None:
        self._reserved = set(reserved_names)
        self._counter = 1

    def fresh(self, base: str = "v") -> str:
        _validate_name(base)
        while True:
            candidate = f"{base}_{self._counter}"
            self._counter += 1
            if candidate not in self._reserved:
                self._reserved.add(candidate)
                return candidate


def _rename_bound_occurrences(term: Term, old: str, new: str) -> Term:
    """Rename an enclosing binder's uses; new must be globally fresh.

    The caller passes that binder's body. A nested binder of old ends its scope.
    """
    match term:
        case Var(name):
            return Var(new) if name == old else term
        case Lam(name, body):
            if name == old:
                return term
            return Lam(name, _rename_bound_occurrences(body, old, new))
        case App(fn, arg):
            return App(
                _rename_bound_occurrences(fn, old, new),
                _rename_bound_occurrences(arg, old, new),
            )
        case _:
            raise TypeError("expected a target Var, Lam, or App")


def substitute(term: Term, variable: str, replacement: Term) -> Term:
    """Replace free uses of variable without capture, evaluation, or mutation."""
    _validate_name(variable)
    replacement_free = free_vars(replacement)
    fresh_names = FreshNameGenerator(all_names(term) | all_names(replacement) | {variable})

    def walk(current: Term) -> Term:
        match current:
            case Var(name):
                # Insert once: do not recursively substitute inside replacement.
                return replacement if name == variable else current
            case Lam(name, body):
                if name == variable or variable not in free_vars(body):
                    return current
                if name in replacement_free:
                    new_name = fresh_names.fresh(name)
                    body = _rename_bound_occurrences(body, name, new_name)
                    name = new_name
                return Lam(name, walk(body))
            case App(fn, arg):
                return App(walk(fn), walk(arg))
            case _:
                raise TypeError("expected a target Var, Lam, or App")

    return walk(term)


def alpha_equivalent(left: Term, right: Term) -> bool:
    """Compare binding structure, requiring free variable names to match.

    Each scope tuple lists binder names from nearest to farthest. A bound
    occurrence must refer to the same binder depth in both terms.
    """
    def binding_depth(name: str, scope: tuple[str, ...]) -> int | None:
        try:
            return scope.index(name)
        except ValueError:
            return None

    def compare(
        first: Term,
        second: Term,
        first_scope: tuple[str, ...],
        second_scope: tuple[str, ...],
    ) -> bool:
        match first, second:
            case Var(first_name), Var(second_name):
                first_depth = binding_depth(first_name, first_scope)
                second_depth = binding_depth(second_name, second_scope)
                if first_depth is None and second_depth is None:
                    return first_name == second_name
                return first_depth is not None and first_depth == second_depth
            case Lam(first_name, first_body), Lam(second_name, second_body):
                return compare(
                    first_body, second_body,
                    (first_name,) + first_scope, (second_name,) + second_scope,
                )
            case App(first_fn, first_arg), App(second_fn, second_arg):
                return compare(first_fn, second_fn, first_scope, second_scope) and compare(
                    first_arg, second_arg, first_scope, second_scope
                )
            case _:
                return False

    return compare(left, right, (), ())
