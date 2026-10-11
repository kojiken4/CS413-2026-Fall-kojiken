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
