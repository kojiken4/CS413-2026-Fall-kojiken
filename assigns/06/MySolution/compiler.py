"""Compositional visitor compilation from source ASTs into pure lambda terms.

No evaluator or observer is imported. All required source constructors/operators
translate compositionally, including recursive definitions through CBV Z.
"""

from . import encodings as church
from .source_ast import ast
from .source_ops import CompilationError, validate_source
from .target import App, FreshNameGenerator, Lam, Term, Var


_NUMERIC_BUILDERS = {
    "+": church.add, "-": church.subtract, "*": church.multiply,
    "<": church.less_than, "<=": church.less_equal,
    ">": church.greater_than, ">=": church.greater_equal,
    "==": church.equal, "!=": church.not_equal,
}


class _CompileVisitor(ast.D0ExpVisitor[Term]):
    def __init__(self, names: FreshNameGenerator) -> None:
        self.names = names

    def _conditional(self, condition: Term, then_term: Term, else_term: Term) -> Term:
        """Delay both branches and force only the selected thunk with I."""
        then_name, else_name = self.names.fresh("u"), self.names.fresh("v")
        selected = App(App(condition, Lam(then_name, then_term)), Lam(else_name, else_term))
        return App(selected, church.identity(names=self.names))

    def visit_int(self, expression: ast.D0Eint) -> Term:
        return church.numeral(expression.arg1, names=self.names)

    def visit_btf(self, expression: ast.D0Ebtf) -> Term:
        return church.boolean(expression.arg1, names=self.names)

    def visit_var(self, expression: ast.D0Evar) -> Term:
        return Var(expression.arg1)

    def visit_lam(self, expression: ast.D0Elam) -> Term:
        return Lam(expression.arg1, expression.arg2.accept(self))

    def visit_app(self, expression: ast.D0Eapp) -> Term:
        return App(expression.arg1.accept(self), expression.arg2.accept(self))

    def visit_let(self, expression: ast.D0Elet) -> Term:
        initializer = expression.arg2.accept(self)
        body = expression.arg3.accept(self)
        return App(Lam(expression.arg1, body), initializer)

    def visit_op1(self, expression: ast.D0Eop1) -> Term:
        operand = expression.arg1.accept(self)
        return App(church.negation(names=self.names), operand)

    def visit_op2(self, expression: ast.D0Eop2) -> Term:
        left = expression.arg1.accept(self)
        right = expression.arg2.accept(self)
        if expression.name == "and":
            return self._conditional(left, right, church.boolean(False, names=self.names))
        if expression.name == "or":
            return self._conditional(left, church.boolean(True, names=self.names), right)
        operator = _NUMERIC_BUILDERS[expression.name](names=self.names)
        return App(App(operator, left), right)

    def visit_if0(self, expression: ast.D0Eif0) -> Term:
        condition = expression.arg1.accept(self)
        then_term = expression.arg2.accept(self)
        else_term = expression.arg3.accept(self)
        return self._conditional(condition, then_term, else_term)

    def visit_pair(self, expression: ast.D0Epair) -> Term:
        left = expression.arg1.accept(self)
        right = expression.arg2.accept(self)
        return App(App(church.pair(names=self.names), left), right)

    def visit_pfst(self, expression: ast.D0Epfst) -> Term:
        operand = expression.arg1.accept(self)
        return App(church.first(names=self.names), operand)

    def visit_psnd(self, expression: ast.D0Epsnd) -> Term:
        operand = expression.arg1.accept(self)
        return App(church.second(names=self.names), operand)

    def visit_fix(self, expression: ast.D0Efix) -> Term:
        body = expression.arg3.accept(self)
        function = Lam(expression.arg1, Lam(expression.arg2, body))
        return App(church.z_combinator(names=self.names), function)


def compile_expr(source_expression: ast.d0exp) -> Term:
    """Validate every source form, then translate without executing the program."""
    names = FreshNameGenerator(validate_source(source_expression))
    return source_expression.accept(_CompileVisitor(names))
