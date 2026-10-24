"""Closed Church-encoding builders expressed only as pure target ASTs.

Representations follow Assign06 Task 2. A shared name generator lets later
compiler/library assembly reserve surrounding names without changing meanings.
Builders construct syntax; they never execute an encoded program.
"""

from .target import App, FreshNameGenerator, Lam, Var


def numeral(number: int, *, names: FreshNameGenerator | None = None) -> Lam:
    """NUM(n) = lam s. lam z. s applied n times to z, for literal n >= 0."""
    if isinstance(number, bool) or not isinstance(number, int):
        raise TypeError("numeral literal must be a nonnegative integer")
    if number < 0:
        raise ValueError(f"negative numeral literal: {number}")
    names = names if names is not None else FreshNameGenerator()
    step, zero = names.fresh("s"), names.fresh("z")
    body = Var(zero)
    for _ in range(number):
        body = App(Var(step), body)
    return Lam(step, Lam(zero, body))


def boolean(value: bool, *, names: FreshNameGenerator | None = None) -> Lam:
    """TRUE/FALSE select the first/second of two supplied arguments."""
    if not isinstance(value, bool):
        raise TypeError("boolean literal must be True or False")
    names = names if names is not None else FreshNameGenerator()
    first, second = names.fresh("t"), names.fresh("f")
    return Lam(first, Lam(second, Var(first if value else second)))


def identity(*, names: FreshNameGenerator | None = None) -> Lam:
    """I = lam w. w; a closed value suitable as a later thunk's dummy argument."""
    names = names if names is not None else FreshNameGenerator()
    name = names.fresh("w")
    return Lam(name, Var(name))
