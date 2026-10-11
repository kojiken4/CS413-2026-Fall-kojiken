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


def regression_substitution_cases():
    """Scope interactions with explicit outputs under the fresh-name policy."""
    return [
        (
            "nested lambda shadowing",
            ast.D0Elam("y", ast.D0Epair(ast.D0Evar("y"), ast.D0Elam(
                "y", ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("y")),
            ))),
            "x", ast.D0Evar("y"),
            "(lam y_1. (pair y_1 (lam y_2. (pair y y_2))))",
        ),
        (
            "nested let initializer belongs to outer lambda",
            ast.D0Elam("y", ast.D0Elet(
                "y", ast.D0Evar("y"), ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("y")),
            )),
            "x", ast.D0Evar("y"),
            "(lam y_1. (let y_2 = y_1 in (pair y y_2)))",
        ),
        (
            "nested fix function shadowing",
            ast.D0Efix("f", "n", ast.D0Efix(
                "f", "m", ast.D0Epair(ast.D0Evar("x"), ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("n"))),
            )),
            "x", ast.D0Evar("f"),
            "(fix f_1(n). (fix f_2(m). (pair f (f_2 n))))",
        ),
        (
            "nested fix parameter shadowing",
            ast.D0Efix("f", "n", ast.D0Efix(
                "g", "n", ast.D0Epair(ast.D0Evar("x"), ast.D0Epair(ast.D0Evar("f"), ast.D0Evar("n"))),
            )),
            "x", ast.D0Evar("n"),
            "(fix f(n_1). (fix g(n_2). (pair n (pair f n_2))))",
        ),
        (
            "existing bound name collision",
            ast.D0Elam("y", ast.D0Epair(ast.D0Evar("x"), ast.D0Elam("y_1", ast.D0Evar("y")))),
            "x", ast.D0Evar("y"),
            "(lam y_2. (pair y (lam y_1. y_2)))",
        ),
        (
            "replacement bound name collision",
            ast.D0Elam("y", ast.D0Evar("x")),
            "x", ast.D0Epair(ast.D0Evar("y"), ast.D0Elam("y_1", ast.D0Evar("y_1"))),
            "(lam y_2. (pair y (lam y_1. y_1)))",
        ),
        (
            "substitution target collision",
            ast.D0Elam("y", ast.D0Evar("y_1")),
            "y_1", ast.D0Evar("y"),
            "(lam y_2. y)",
        ),
        (
            "generated names shared across siblings",
            ast.D0Epair(ast.D0Elam("y", ast.D0Evar("x")), ast.D0Elam("y", ast.D0Evar("x"))),
            "x", ast.D0Evar("y"),
            "(pair (lam y_1. y) (lam y_2. y))",
        ),
        (
            "generated names shared across let initializer and body",
            ast.D0Elet("y", ast.D0Elam("y", ast.D0Evar("x")), ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("y"))),
            "x", ast.D0Evar("y"),
            "(let y_2 = (lam y_1. y) in (pair y y_2))",
        ),
        (
            "no renaming when target is shadowed deeper",
            ast.D0Elam("y", ast.D0Elam("x", ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("y")))),
            "x", ast.D0Evar("y"),
            "(lam y. (lam x. (pair x y)))",
        ),
        (
            "no renaming in fix without a free target",
            ast.D0Efix("f", "n", ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("n"))),
            "x", ast.D0Epair(ast.D0Evar("f"), ast.D0Evar("n")),
            "(fix f(n). (f n))",
        ),
        (
            "no renaming in let without a free target",
            ast.D0Elet("y", ast.D0Eint(1), ast.D0Evar("y")),
            "x", ast.D0Evar("y"),
            "(let y = 1 in y)",
        ),
        (
            "equal fix names under nested parameter shadowing",
            ast.D0Efix("f", "f", ast.D0Epair(
                ast.D0Evar("f"), ast.D0Elam("f", ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("f"))),
            )),
            "x", ast.D0Evar("f"),
            "(fix f_1(f_1). (pair f_1 (lam f_2. (pair f f_2))))",
        ),
    ]
