"""One evaluation loop for source ASTs and pure target terms.

Source operations provide a baseline for compiler checks. Target execution uses
only target syntax and substitution; source arithmetic is never a target shortcut.
The supplied module contributes syntax/value/environment records, not evaluation.
"""

from dataclasses import dataclass
from typing import Literal

from .source_ast import ast
from .target import App, Lam, Term, Var, free_vars, substitute


class OpenTermError(ValueError):
    """Execution requires a closed target term; structural operations do not."""


class SourceEvaluationError(ValueError):
    """An evaluated source expression is unsupported, unbound, or misused."""


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    status: Literal["completed", "exhausted"]
    term: Term | ast.d0val
    steps: int | None
    budget: int | None

    @property
    def value(self) -> Lam | ast.d0val | None:
        """Expose a value only after successful completion."""
        if self.status == "completed" and isinstance(self.term, (Lam, ast.D0V000)):
            return self.term
        return None


@dataclass(frozen=True, slots=True)
class _EvaluateArgument:
    """The function is being evaluated; its argument must wait."""
    arg: Term | ast.d0exp
    env: ast.d0env


@dataclass(frozen=True, slots=True)
class _Apply:
    """The function is a value; wait for its argument before applying it."""
    fn: Lam | ast.d0val


@dataclass(frozen=True, slots=True)
class _Conditional:
    then_branch: ast.d0exp
    else_branch: ast.d0exp
    env: ast.d0env


@dataclass(frozen=True, slots=True)
class _Let:
    name: str
    body: ast.d0exp
    env: ast.d0env


@dataclass(frozen=True, slots=True)
class _Unary:
    operator: str


@dataclass(frozen=True, slots=True)
class _BinaryLeft:
    operator: str
    right: ast.d0exp
    env: ast.d0env


@dataclass(frozen=True, slots=True)
class _BinaryRight:
    operator: str
    left: ast.d0val


@dataclass(frozen=True, slots=True)
class _PairLeft:
    right: ast.d0exp
    env: ast.d0env


@dataclass(frozen=True, slots=True)
class _PairRight:
    left: ast.d0val


@dataclass(frozen=True, slots=True)
class _Projection:
    first: bool


type _Frame = (
    _EvaluateArgument | _Apply | _Conditional | _Let | _Unary
    | _BinaryLeft | _BinaryRight | _PairLeft | _PairRight | _Projection
)


_BINARY_OPERATORS = frozenset({
    "+", "-", "*", "<", "<=", ">", ">=", "==", "!=", "and", "or",
})


def _lookup(env: ast.d0env, name: str) -> ast.d0val:
    while isinstance(env, ast.ENVcns):
        if env.arg1 == name:
            return env.arg2
        env = env.arg3
    raise SourceEvaluationError(f"unbound source variable: {name}")


def _natural(value: ast.d0val) -> int:
    if not isinstance(value, ast.D0Vint):
        raise SourceEvaluationError("expected a source natural-number value")
    return value.arg1


def _boolean(value: ast.d0val) -> bool:
    if not isinstance(value, ast.D0Vbtf):
        raise SourceEvaluationError("expected a source boolean value")
    return value.arg1


def _apply_source_binary(operator: str, left: ast.d0val, right: ast.d0val) -> ast.d0val:
    """Combine already evaluated source operands; never called for target terms."""
    if operator in ("and", "or"):
        # The left frame already decided that the right operand was needed.
        return ast.D0Vbtf(_boolean(right))

    first, second = _natural(left), _natural(right)
    match operator:
        case "+":
            return ast.D0Vint(first + second)
        case "-":
            return ast.D0Vint(max(first - second, 0))
        case "*":
            return ast.D0Vint(first * second)
        case "<":
            return ast.D0Vbtf(first < second)
        case "<=":
            return ast.D0Vbtf(first <= second)
        case ">":
            return ast.D0Vbtf(first > second)
        case ">=":
            return ast.D0Vbtf(first >= second)
        case "==":
            return ast.D0Vbtf(first == second)
        case "!=":
            return ast.D0Vbtf(first != second)
        case _:
            raise SourceEvaluationError(f"unsupported binary operator: {operator!r}")


def _rebuild_term(current: Term, frames: list[_Frame]) -> Term:
    """Put an unfinished expression back into its surrounding applications."""
    for frame in reversed(frames):
        match frame:
            case _EvaluateArgument(arg, _):
                current = App(current, arg)
            case _Apply(fn):
                current = App(fn, current)
            case _:
                raise RuntimeError("source continuation in target execution")
    return current


def evaluate(
    expression: Term | ast.d0exp, *, max_steps: int | None = None,
) -> EvaluationResult:
    """Evaluate either language with one weak, left-to-right call-by-value loop.

    Target calls require a nonnegative integer budget, counting beta-value steps
    only. Source calls omit the budget and return a supplied D0V value with no
    target step count. Known divergent source programs must not be run here.
    """
    target_mode = isinstance(expression, (Var, Lam, App))
    if target_mode:
        if isinstance(max_steps, bool) or not isinstance(max_steps, int):
            raise TypeError("max_steps must be a nonnegative integer")
        if max_steps < 0:
            raise ValueError("max_steps must be nonnegative")
        free = free_vars(expression)
        if free:
            raise OpenTermError(
                "target execution requires a closed term; free variables: "
                + ", ".join(sorted(free))
            )
    elif isinstance(expression, ast.D0E000):
        if max_steps is not None:
            raise TypeError("source evaluation is unbounded; omit max_steps")
    else:
        raise TypeError("expected a source expression or target Var, Lam, or App")

    current = expression
    env = ast.ENVnil()
    frames: list[_Frame] = []
    steps = 0

    while True:
        match current:
            case App(fn, arg) | ast.D0Eapp(fn, arg):
                frames.append(_EvaluateArgument(arg, env))
                current = fn
                continue
            case Var(name) | ast.D0Evar(name):
                if target_mode:
                    raise OpenTermError(f"cannot execute unbound target variable: {name}")
                current = _lookup(env, name)
            case Lam():
                pass
            case ast.D0Elam():
                current = ast.D0Vlam(env, current)
            case ast.D0Efix():
                current = ast.D0Vfix(env, current)
            case ast.D0Eint(number):
                if number < 0:
                    raise SourceEvaluationError(f"negative literal is unsupported: {number}")
                current = ast.D0Vint(number)
            case ast.D0Ebtf(boolean):
                current = ast.D0Vbtf(boolean)
            case ast.D0Eop1(operator, arg):
                if operator != "not":
                    raise SourceEvaluationError(f"unsupported unary operator: {operator!r}")
                frames.append(_Unary(operator))
                current = arg
                continue
            case ast.D0Eop2(operator, left, right):
                if operator not in _BINARY_OPERATORS:
                    raise SourceEvaluationError(f"unsupported binary operator: {operator!r}")
                frames.append(_BinaryLeft(operator, right, env))
                current = left
                continue
            case ast.D0Eif0(condition, then_branch, else_branch):
                frames.append(_Conditional(then_branch, else_branch, env))
                current = condition
                continue
            case ast.D0Elet(name, initializer, body):
                frames.append(_Let(name, body, env))
                current = initializer
                continue
            case ast.D0Epair(left, right):
                frames.append(_PairLeft(right, env))
                current = left
                continue
            case ast.D0Epfst(pair):
                frames.append(_Projection(True))
                current = pair
                continue
            case ast.D0Epsnd(pair):
                frames.append(_Projection(False))
                current = pair
                continue
            case ast.D0V000():
                # A frame may have constructed a value on the preceding iteration.
                pass
            case _:
                raise TypeError("expected source or target syntax")

        # Both languages deliver values to the same continuation stack.
        if not frames:
            return EvaluationResult(
                "completed", current, steps if target_mode else None, max_steps,
            )

        frame = frames.pop()
        match frame:
            case _EvaluateArgument(arg, saved_env):
                frames.append(_Apply(current))
                current, env = arg, saved_env
            case _Apply(fn):
                if target_mode:
                    # Both operands are lambda values. Check before contracting.
                    if steps == max_steps:
                        residual = _rebuild_term(App(fn, current), frames)
                        return EvaluationResult("exhausted", residual, steps, max_steps)
                    current = substitute(fn.body, fn.name, current)
                    steps += 1
                elif isinstance(fn, ast.D0Vlam):
                    function = fn.arg2
                    env = ast.ENVcns(function.arg1, current, fn.arg1)
                    current = function.arg2
                elif isinstance(fn, ast.D0Vfix):
                    function = fn.arg2
                    env = ast.ENVcns(function.arg1, fn, fn.arg1)
                    # Add the parameter last: it shadows a coincident function name.
                    env = ast.ENVcns(function.arg2, current, env)
                    current = function.arg3
                else:
                    raise SourceEvaluationError("application expected a source function")
            case _Conditional(then_branch, else_branch, saved_env):
                current = then_branch if _boolean(current) else else_branch
                env = saved_env
            case _Let(name, body, saved_env):
                env = ast.ENVcns(name, current, saved_env)
                current = body
            case _Unary("not"):
                current = ast.D0Vbtf(not _boolean(current))
            case _BinaryLeft(operator, right, saved_env):
                env = saved_env
                if operator == "and" and not _boolean(current):
                    current = ast.D0Vbtf(False)
                elif operator == "or" and _boolean(current):
                    current = ast.D0Vbtf(True)
                else:
                    frames.append(_BinaryRight(operator, current))
                    current = right
            case _BinaryRight(operator, left):
                current = _apply_source_binary(operator, left, current)
            case _PairLeft(right, saved_env):
                frames.append(_PairRight(current))
                current, env = right, saved_env
            case _PairRight(left):
                current = ast.D0Vpair(left, current)
            case _Projection(first):
                if not isinstance(current, ast.D0Vpair):
                    raise SourceEvaluationError("projection expected a source pair")
                current = current.arg1 if first else current.arg2
