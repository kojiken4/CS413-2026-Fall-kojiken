"""Visitor operations for Assignment 05.

The supplied AST and visitor interface live in the parent lambda1_vp module.
"""

import lambda1_vp as ast


class PrettyPrintVisitor(ast.D0ExpVisitor[str]):
    """Render expression syntax without evaluating or changing the AST."""

    def visit_int(self, expression: ast.D0Eint) -> str:
        return str(expression.arg1)

    def visit_btf(self, expression: ast.D0Ebtf) -> str:
        return "true" if expression.arg1 else "false"

    def visit_var(self, expression: ast.D0Evar) -> str:
        return expression.arg1

    def visit_op1(self, expression: ast.D0Eop1) -> str:
        return f"({expression.name} {expression.arg1.accept(self)})"

    def visit_op2(self, expression: ast.D0Eop2) -> str:
        return (
            f"({expression.arg1.accept(self)} {expression.name} "
            f"{expression.arg2.accept(self)})"
        )

    def visit_lam(self, expression: ast.D0Elam) -> str:
        return f"(lam {expression.arg1}. {expression.arg2.accept(self)})"

    def visit_fix(self, expression: ast.D0Efix) -> str:
        return (
            f"(fix {expression.arg1}({expression.arg2}). "
            f"{expression.arg3.accept(self)})"
        )

    def visit_app(self, expression: ast.D0Eapp) -> str:
        return f"({expression.arg1.accept(self)} {expression.arg2.accept(self)})"

    def visit_if0(self, expression: ast.D0Eif0) -> str:
        return (
            f"(if {expression.arg1.accept(self)} "
            f"then {expression.arg2.accept(self)} "
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


def d0exp_pretty(expression: ast.d0exp) -> str:
    """Return the assignment's exact single-line representation."""
    return expression.accept(PrettyPrintVisitor())


class AllNamesVisitor(ast.D0ExpVisitor[frozenset[str]]):
    """Collect all variable and binder names, including unused bound names."""

    def visit_int(self, expression: ast.D0Eint) -> frozenset[str]:
        return frozenset()

    def visit_btf(self, expression: ast.D0Ebtf) -> frozenset[str]:
        return frozenset()

    def visit_var(self, expression: ast.D0Evar) -> frozenset[str]:
        return frozenset({expression.arg1})

    def visit_op1(self, expression: ast.D0Eop1) -> frozenset[str]:
        return expression.arg1.accept(self)

    def visit_op2(self, expression: ast.D0Eop2) -> frozenset[str]:
        return expression.arg1.accept(self) | expression.arg2.accept(self)

    def visit_lam(self, expression: ast.D0Elam) -> frozenset[str]:
        return expression.arg2.accept(self) | {expression.arg1}

    def visit_fix(self, expression: ast.D0Efix) -> frozenset[str]:
        return expression.arg3.accept(self) | {expression.arg1, expression.arg2}

    def visit_app(self, expression: ast.D0Eapp) -> frozenset[str]:
        return expression.arg1.accept(self) | expression.arg2.accept(self)

    def visit_if0(self, expression: ast.D0Eif0) -> frozenset[str]:
        return (
            expression.arg1.accept(self)
            | expression.arg2.accept(self)
            | expression.arg3.accept(self)
        )

    def visit_let(self, expression: ast.D0Elet) -> frozenset[str]:
        return (
            expression.arg2.accept(self)
            | expression.arg3.accept(self)
            | {expression.arg1}
        )

    def visit_pair(self, expression: ast.D0Epair) -> frozenset[str]:
        return expression.arg1.accept(self) | expression.arg2.accept(self)

    def visit_pfst(self, expression: ast.D0Epfst) -> frozenset[str]:
        return expression.arg1.accept(self)

    def visit_psnd(self, expression: ast.D0Epsnd) -> frozenset[str]:
        return expression.arg1.accept(self)


class ScopedRenameVisitor(ast.D0ExpVisitor[ast.d0exp]):
    """Rename free occurrences within a region without changing its binders.

    The new name must be globally fresh. For alpha-renaming an outer binder,
    visit its body with this helper and update that binder's declaration in the
    caller. Nested binders of the old name stop renaming in their own bodies.
    """

    def __init__(self, old_name: str, new_name: str) -> None:
        self.old_name = old_name
        self.new_name = new_name

    def visit_int(self, expression: ast.D0Eint) -> ast.d0exp:
        return expression

    def visit_btf(self, expression: ast.D0Ebtf) -> ast.d0exp:
        return expression

    def visit_var(self, expression: ast.D0Evar) -> ast.d0exp:
        if expression.arg1 == self.old_name:
            return ast.D0Evar(self.new_name)
        return expression

    def visit_op1(self, expression: ast.D0Eop1) -> ast.d0exp:
        return ast.D0Eop1(expression.name, expression.arg1.accept(self))

    def visit_op2(self, expression: ast.D0Eop2) -> ast.d0exp:
        return ast.D0Eop2(
            expression.name, expression.arg1.accept(self), expression.arg2.accept(self)
        )

    def visit_lam(self, expression: ast.D0Elam) -> ast.d0exp:
        if expression.arg1 == self.old_name:
            return expression
        return ast.D0Elam(expression.arg1, expression.arg2.accept(self))

    def visit_fix(self, expression: ast.D0Efix) -> ast.d0exp:
        if self.old_name in (expression.arg1, expression.arg2):
            return expression
        return ast.D0Efix(
            expression.arg1, expression.arg2, expression.arg3.accept(self)
        )

    def visit_app(self, expression: ast.D0Eapp) -> ast.d0exp:
        return ast.D0Eapp(expression.arg1.accept(self), expression.arg2.accept(self))

    def visit_if0(self, expression: ast.D0Eif0) -> ast.d0exp:
        return ast.D0Eif0(
            expression.arg1.accept(self),
            expression.arg2.accept(self),
            expression.arg3.accept(self),
        )

    def visit_let(self, expression: ast.D0Elet) -> ast.d0exp:
        initializer = expression.arg2.accept(self)
        body = expression.arg3
        if expression.arg1 != self.old_name:
            body = body.accept(self)
        return ast.D0Elet(expression.arg1, initializer, body)

    def visit_pair(self, expression: ast.D0Epair) -> ast.d0exp:
        return ast.D0Epair(expression.arg1.accept(self), expression.arg2.accept(self))

    def visit_pfst(self, expression: ast.D0Epfst) -> ast.d0exp:
        return ast.D0Epfst(expression.arg1.accept(self))

    def visit_psnd(self, expression: ast.D0Epsnd) -> ast.d0exp:
        return ast.D0Epsnd(expression.arg1.accept(self))


class FreshNameGenerator:
    """Generate base_counter names using one counter for this instance.

    Callers reserve all names from both input ASTs and the substitution target.
    Create a new generator for each substitution call and share it throughout
    that call. Every attempted candidate advances the counter, including names
    skipped because they are already reserved.
    """

    def __init__(self, reserved_names: frozenset[str]) -> None:
        self._reserved = set(reserved_names)
        self._counter = 1

    def fresh(self, base: str) -> str:
        while True:
            candidate = f"{base}_{self._counter}"
            self._counter += 1
            if candidate not in self._reserved:
                self._reserved.add(candidate)
                return candidate
