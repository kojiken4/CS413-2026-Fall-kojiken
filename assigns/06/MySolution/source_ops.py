"""Source printing and whole-AST checks without execution or input mutation.

The printer and name-collection traversal adapt Assignment 5 MySolution/operations.py.
Checks use Assignment 6's narrower literals/operators, including recursive bodies.
"""

import re

from .source_ast import ast


class CompilationError(ValueError):
    """Source syntax is unsupported by the assignment's compilation language."""


_BINARY_OPERATORS = frozenset({
    "+", "-", "*", "<", "<=", ">", ">=", "==", "!=", "and", "or",
})


class _SourceCheckVisitor(ast.D0ExpVisitor[frozenset[str]]):
    """Validate every child and collect all variable and binder names."""

    def _name(self, name: str) -> frozenset[str]:
        if not isinstance(name, str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise CompilationError(f"invalid source identifier: {name!r}")
        return frozenset({name})

    def visit_int(self, expression: ast.D0Eint) -> frozenset[str]:
        if expression.arg1 < 0:
            raise CompilationError(f"negative literal is unsupported: {expression.arg1}")
        return frozenset()

    def visit_btf(self, expression: ast.D0Ebtf) -> frozenset[str]:
        return frozenset()

    def visit_var(self, expression: ast.D0Evar) -> frozenset[str]:
        return self._name(expression.arg1)

    def visit_lam(self, expression: ast.D0Elam) -> frozenset[str]:
        return self._name(expression.arg1) | expression.arg2.accept(self)

    def visit_fix(self, expression: ast.D0Efix) -> frozenset[str]:
        return (
            self._name(expression.arg1) | self._name(expression.arg2)
            | expression.arg3.accept(self)
        )

    def visit_app(self, expression: ast.D0Eapp) -> frozenset[str]:
        return expression.arg1.accept(self) | expression.arg2.accept(self)

    def visit_op1(self, expression: ast.D0Eop1) -> frozenset[str]:
        if expression.name != "not":
            raise CompilationError(f"unsupported unary operator: {expression.name!r}")
        return expression.arg1.accept(self)

    def visit_op2(self, expression: ast.D0Eop2) -> frozenset[str]:
        if expression.name not in _BINARY_OPERATORS:
            raise CompilationError(f"unsupported binary operator: {expression.name!r}")
        return expression.arg1.accept(self) | expression.arg2.accept(self)

    def visit_if0(self, expression: ast.D0Eif0) -> frozenset[str]:
        return (
            expression.arg1.accept(self) | expression.arg2.accept(self)
            | expression.arg3.accept(self)
        )

    def visit_let(self, expression: ast.D0Elet) -> frozenset[str]:
        return self._name(expression.arg1) | expression.arg2.accept(self) | expression.arg3.accept(self)

    def visit_pair(self, expression: ast.D0Epair) -> frozenset[str]:
        return expression.arg1.accept(self) | expression.arg2.accept(self)

    def visit_pfst(self, expression: ast.D0Epfst) -> frozenset[str]:
        return expression.arg1.accept(self)

    def visit_psnd(self, expression: ast.D0Epsnd) -> frozenset[str]:
        return expression.arg1.accept(self)


def validate_source(expression: ast.d0exp) -> frozenset[str]:
    """Validate the full source syntax and return all names, including unused binders."""
    if not isinstance(expression, ast.D0E000):
        raise CompilationError(f"expected a source expression, got {type(expression).__name__}")
    try:
        return expression.accept(_SourceCheckVisitor())
    except TypeError as error:
        raise CompilationError(str(error)) from error


class _SourcePrintVisitor(ast.D0ExpVisitor[str]):
    """Render syntax literally, including invalid operators for diagnostics."""

    def visit_int(self, expression: ast.D0Eint) -> str:
        return str(expression.arg1)

    def visit_btf(self, expression: ast.D0Ebtf) -> str:
        return "true" if expression.arg1 else "false"

    def visit_var(self, expression: ast.D0Evar) -> str:
        return expression.arg1

    def visit_lam(self, expression: ast.D0Elam) -> str:
        return f"(lam {expression.arg1}. {expression.arg2.accept(self)})"

    def visit_fix(self, expression: ast.D0Efix) -> str:
        return f"(fix {expression.arg1}({expression.arg2}). {expression.arg3.accept(self)})"

    def visit_app(self, expression: ast.D0Eapp) -> str:
        return f"({expression.arg1.accept(self)} {expression.arg2.accept(self)})"

    def visit_op1(self, expression: ast.D0Eop1) -> str:
        return f"({expression.name} {expression.arg1.accept(self)})"

    def visit_op2(self, expression: ast.D0Eop2) -> str:
        return f"({expression.arg1.accept(self)} {expression.name} {expression.arg2.accept(self)})"

    def visit_if0(self, expression: ast.D0Eif0) -> str:
        return (
            f"(if {expression.arg1.accept(self)} then {expression.arg2.accept(self)} "
            f"else {expression.arg3.accept(self)})"
        )

    def visit_let(self, expression: ast.D0Elet) -> str:
        return (
            f"(let {expression.arg1} = {expression.arg2.accept(self)} "
            f"in {expression.arg3.accept(self)})"
        )

    def visit_pair(self, expression: ast.D0Epair) -> str:
        return f"(pair {expression.arg1.accept(self)} {expression.arg2.accept(self)})"

    def visit_pfst(self, expression: ast.D0Epfst) -> str:
        return f"(fst {expression.arg1.accept(self)})"

    def visit_psnd(self, expression: ast.D0Epsnd) -> str:
        return f"(snd {expression.arg1.accept(self)})"


def pretty_source(expression: ast.d0exp) -> str:
    """Print an AST without validation, evaluation, or mutation."""
    return expression.accept(_SourcePrintVisitor())
