"""Closed Church-encoding builders expressed only as pure target ASTs.

Representations follow Assign06 Task 2. A shared name generator lets later
compiler/library assembly reserve surrounding names without changing meanings.
Builders construct syntax; they never execute an encoded program.
"""

from .target import App, FreshNameGenerator, Lam, Term, Var


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


def _apply(fn: Term, *arguments: Term) -> Term:
    """Build left-associated application syntax without evaluating it."""
    for argument in arguments:
        fn = App(fn, argument)
    return fn


def pair(*, names: FreshNameGenerator | None = None) -> Lam:
    """PAIR = lam a. lam b. lam p. p a b."""
    names = names if names is not None else FreshNameGenerator()
    left, right, selector = names.fresh("a"), names.fresh("b"), names.fresh("p")
    return Lam(left, Lam(right, Lam(selector, _apply(Var(selector), Var(left), Var(right)))))


def first(*, names: FreshNameGenerator | None = None) -> Lam:
    """FST = lam p. p TRUE."""
    names = names if names is not None else FreshNameGenerator()
    name = names.fresh("p")
    return Lam(name, App(Var(name), boolean(True, names=names)))


def second(*, names: FreshNameGenerator | None = None) -> Lam:
    """SND = lam p. p FALSE."""
    names = names if names is not None else FreshNameGenerator()
    name = names.fresh("p")
    return Lam(name, App(Var(name), boolean(False, names=names)))


def successor(*, names: FreshNameGenerator | None = None) -> Lam:
    """SUCC n applies the supplied step once more than n does."""
    names = names if names is not None else FreshNameGenerator()
    number, step, zero = names.fresh("n"), names.fresh("s"), names.fresh("z")
    return Lam(number, Lam(step, Lam(zero,
        App(Var(step), _apply(Var(number), Var(step), Var(zero))),
    )))


def predecessor(*, names: FreshNameGenerator | None = None) -> Lam:
    """Iterate (previous, current) -> (current, SUCC current) from (0, 0)."""
    names = names if names is not None else FreshNameGenerator()
    number, state = names.fresh("n"), names.fresh("state")
    current = App(second(names=names), Var(state))
    update = Lam(state, _apply(
        pair(names=names), current, App(successor(names=names), current),
    ))
    initial = _apply(pair(names=names), numeral(0, names=names), numeral(0, names=names))
    return Lam(number, App(first(names=names), _apply(Var(number), update, initial)))


def is_zero(*, names: FreshNameGenerator | None = None) -> Lam:
    """ISZERO n repeats a constant-FALSE step starting from TRUE."""
    names = names if names is not None else FreshNameGenerator()
    number, ignored = names.fresh("n"), names.fresh("ignored")
    step = Lam(ignored, boolean(False, names=names))
    return Lam(number, _apply(Var(number), step, boolean(True, names=names)))


def add(*, names: FreshNameGenerator | None = None) -> Lam:
    """ADD m n s z = m s (n s z)."""
    names = names if names is not None else FreshNameGenerator()
    left, right, step, zero = (names.fresh(base) for base in ("m", "n", "s", "z"))
    body = _apply(Var(left), Var(step), _apply(Var(right), Var(step), Var(zero)))
    return Lam(left, Lam(right, Lam(step, Lam(zero, body))))


def subtract(*, names: FreshNameGenerator | None = None) -> Lam:
    """SUB m n = n PRED m; repeated predecessor truncates at zero."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("m"), names.fresh("n")
    return Lam(left, Lam(right, _apply(Var(right), predecessor(names=names), Var(left))))


def multiply(*, names: FreshNameGenerator | None = None) -> Lam:
    """MUL m n s z = m (n s) z."""
    names = names if names is not None else FreshNameGenerator()
    left, right, step, zero = (names.fresh(base) for base in ("m", "n", "s", "z"))
    body = _apply(Var(left), App(Var(right), Var(step)), Var(zero))
    return Lam(left, Lam(right, Lam(step, Lam(zero, body))))


def negation(*, names: FreshNameGenerator | None = None) -> Lam:
    """NOT p = p FALSE TRUE."""
    names = names if names is not None else FreshNameGenerator()
    name = names.fresh("p")
    return Lam(name, _apply(Var(name), boolean(False, names=names), boolean(True, names=names)))


def conjunction(*, names: FreshNameGenerator | None = None) -> Lam:
    """AND p q = p q FALSE, accepting two already evaluated booleans.

    Source short-circuit compilation must delay the right computation separately.
    """
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("p"), names.fresh("q")
    return Lam(left, Lam(right, _apply(Var(left), Var(right), boolean(False, names=names))))


def disjunction(*, names: FreshNameGenerator | None = None) -> Lam:
    """OR p q = p TRUE q, accepting two already evaluated booleans."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("p"), names.fresh("q")
    return Lam(left, Lam(right, _apply(Var(left), boolean(True, names=names), Var(right))))


def less_equal(*, names: FreshNameGenerator | None = None) -> Lam:
    """LE m n = ISZERO (SUB m n)."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("m"), names.fresh("n")
    difference = _apply(subtract(names=names), Var(left), Var(right))
    return Lam(left, Lam(right, App(is_zero(names=names), difference)))


def less_than(*, names: FreshNameGenerator | None = None) -> Lam:
    """LT m n = NOT (LE n m)."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("m"), names.fresh("n")
    reversed_le = _apply(less_equal(names=names), Var(right), Var(left))
    return Lam(left, Lam(right, App(negation(names=names), reversed_le)))


def greater_equal(*, names: FreshNameGenerator | None = None) -> Lam:
    """GE m n = LE n m."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("m"), names.fresh("n")
    return Lam(left, Lam(right, _apply(less_equal(names=names), Var(right), Var(left))))


def greater_than(*, names: FreshNameGenerator | None = None) -> Lam:
    """GT m n = LT n m."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("m"), names.fresh("n")
    return Lam(left, Lam(right, _apply(less_than(names=names), Var(right), Var(left))))


def equal(*, names: FreshNameGenerator | None = None) -> Lam:
    """EQ m n = AND (LE m n) (LE n m), for naturals only."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("m"), names.fresh("n")
    forward = _apply(less_equal(names=names), Var(left), Var(right))
    backward = _apply(less_equal(names=names), Var(right), Var(left))
    return Lam(left, Lam(right, _apply(conjunction(names=names), forward, backward)))


def not_equal(*, names: FreshNameGenerator | None = None) -> Lam:
    """NE m n = NOT (EQ m n)."""
    names = names if names is not None else FreshNameGenerator()
    left, right = names.fresh("m"), names.fresh("n")
    equality = _apply(equal(names=names), Var(left), Var(right))
    return Lam(left, Lam(right, App(negation(names=names), equality)))


def z_combinator(*, names: FreshNameGenerator | None = None) -> Lam:
    """CBV Z = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))."""
    names = names if names is not None else FreshNameGenerator()
    function = names.fresh("g")

    def arm() -> Lam:
        self_name, argument = names.fresh("x"), names.fresh("v")
        delayed_call = Lam(argument, _apply(Var(self_name), Var(self_name), Var(argument)))
        return Lam(self_name, App(Var(function), delayed_call))

    return Lam(function, App(arm(), arm()))
