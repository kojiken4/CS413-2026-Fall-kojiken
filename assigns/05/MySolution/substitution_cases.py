"""Shared substitution inputs and explicit structural expectations."""

import lambda1_vp as ast


def constructor_substitution_cases():
    """Substitute x := 3 through every expression constructor."""
    return [
        (ast.D0Eint(7), ast.D0Eint(7)),
        (ast.D0Ebtf(True), ast.D0Ebtf(True)),
        (ast.D0Evar("x"), ast.D0Eint(3)),
        (ast.D0Evar("z"), ast.D0Evar("z")),
        (ast.D0Eop1("+1", ast.D0Evar("x")), ast.D0Eop1("+1", ast.D0Eint(3))),
        (ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("x")), ast.D0Eop2("+", ast.D0Eint(3), ast.D0Eint(3))),
        (ast.D0Elam("y", ast.D0Evar("x")), ast.D0Elam("y", ast.D0Eint(3))),
        (ast.D0Efix("f", "n", ast.D0Evar("x")), ast.D0Efix("f", "n", ast.D0Eint(3))),
        (ast.D0Eapp(ast.D0Evar("x"), ast.D0Evar("x")), ast.D0Eapp(ast.D0Eint(3), ast.D0Eint(3))),
        (
            ast.D0Eif0(ast.D0Evar("x"), ast.D0Evar("x"), ast.D0Evar("x")),
            ast.D0Eif0(ast.D0Eint(3), ast.D0Eint(3), ast.D0Eint(3)),
        ),
        (
            ast.D0Elet("y", ast.D0Evar("x"), ast.D0Evar("x")),
            ast.D0Elet("y", ast.D0Eint(3), ast.D0Eint(3)),
        ),
        (ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("x")), ast.D0Epair(ast.D0Eint(3), ast.D0Eint(3))),
        (ast.D0Epfst(ast.D0Evar("x")), ast.D0Epfst(ast.D0Eint(3))),
        (ast.D0Epsnd(ast.D0Evar("x")), ast.D0Epsnd(ast.D0Eint(3))),
    ]


def binding_substitution_cases():
    """Return expression, target, replacement, expected expression tuples."""
    return [
        (
            ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("z")), "x", ast.D0Eint(3),
            ast.D0Eop2("+", ast.D0Eint(3), ast.D0Evar("z")),
        ),
        (
            ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))), "x", ast.D0Eint(3),
            ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))),
        ),
        (
            ast.D0Elam("y", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))), "x", ast.D0Evar("y"),
            ast.D0Elam("y_1", ast.D0Eop2("+", ast.D0Evar("y"), ast.D0Evar("y_1"))),
        ),
        (
            ast.D0Elet("x", ast.D0Evar("x"), ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))), "x", ast.D0Eint(3),
            ast.D0Elet("x", ast.D0Eint(3), ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))),
        ),
        (
            ast.D0Elet("y", ast.D0Evar("x"), ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))), "x", ast.D0Evar("y"),
            ast.D0Elet("y_1", ast.D0Evar("y"), ast.D0Eop2("+", ast.D0Evar("y"), ast.D0Evar("y_1"))),
        ),
        (
            ast.D0Efix("f", "n", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("n")))), "x", ast.D0Evar("f"),
            ast.D0Efix("f_1", "n", ast.D0Eop2("+", ast.D0Evar("f"), ast.D0Eapp(ast.D0Evar("f_1"), ast.D0Evar("n")))),
        ),
        (
            ast.D0Evar("x"), "x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)),
            ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)),
        ),
        (ast.D0Efix("x", "n", ast.D0Evar("x")), "x", ast.D0Eint(3), ast.D0Efix("x", "n", ast.D0Evar("x"))),
        (ast.D0Efix("f", "x", ast.D0Evar("x")), "x", ast.D0Eint(3), ast.D0Efix("f", "x", ast.D0Evar("x"))),
        (ast.D0Efix("x", "x", ast.D0Evar("x")), "x", ast.D0Eint(3), ast.D0Efix("x", "x", ast.D0Evar("x"))),
        (
            ast.D0Efix("f", "n", ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("n"))), "x", ast.D0Evar("n"),
            ast.D0Efix("f", "n_1", ast.D0Epair(ast.D0Evar("n"), ast.D0Evar("n_1"))),
        ),
        (
            ast.D0Efix("f", "n", ast.D0Epair(ast.D0Evar("x"), ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("n")))),
            "x", ast.D0Epair(ast.D0Evar("f"), ast.D0Evar("n")),
            ast.D0Efix("f_1", "n_2", ast.D0Epair(
                ast.D0Epair(ast.D0Evar("f"), ast.D0Evar("n")),
                ast.D0Eapp(ast.D0Evar("f_1"), ast.D0Evar("n_2")),
            )),
        ),
        (
            ast.D0Efix("f", "f", ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("f"))), "x", ast.D0Evar("f"),
            ast.D0Efix("f_1", "f_1", ast.D0Epair(ast.D0Evar("f"), ast.D0Evar("f_1"))),
        ),
        (ast.D0Elam("y", ast.D0Evar("z")), "x", ast.D0Evar("y"), ast.D0Elam("y", ast.D0Evar("z"))),
        (
            ast.D0Elet("y", ast.D0Evar("x"), ast.D0Evar("y")), "x", ast.D0Evar("y"),
            ast.D0Elet("y", ast.D0Evar("y"), ast.D0Evar("y")),
        ),
        (
            ast.D0Elam("y", ast.D0Evar("x")), "x", ast.D0Elam("y", ast.D0Evar("y")),
            ast.D0Elam("y", ast.D0Elam("y", ast.D0Evar("y"))),
        ),
    ]
