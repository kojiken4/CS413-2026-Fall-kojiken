"""Shared example inputs and explicit expectations for both helper test suites."""

import lambda1_vp as ast


def all_names_cases():
    """Include every constructor and unused binder declarations."""
    return [
        (ast.D0Eint(5), frozenset()),
        (ast.D0Ebtf(False), frozenset()),
        (ast.D0Evar("x"), frozenset({"x"})),
        (ast.D0Eop1("operator", ast.D0Evar("x")), frozenset({"x"})),
        (ast.D0Eop2("operator", ast.D0Evar("x"), ast.D0Evar("y")), frozenset({"x", "y"})),
        (ast.D0Elam("unused", ast.D0Evar("x")), frozenset({"unused", "x"})),
        (ast.D0Efix("f", "n", ast.D0Evar("x")), frozenset({"f", "n", "x"})),
        (ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("x")), frozenset({"f", "x"})),
        (ast.D0Eif0(ast.D0Evar("c"), ast.D0Evar("t"), ast.D0Evar("e")), frozenset({"c", "t", "e"})),
        (ast.D0Elet("unused", ast.D0Evar("init"), ast.D0Evar("body")), frozenset({"unused", "init", "body"})),
        (ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("y")), frozenset({"x", "y"})),
        (ast.D0Epfst(ast.D0Evar("p")), frozenset({"p"})),
        (ast.D0Epsnd(ast.D0Evar("p")), frozenset({"p"})),
        (
            ast.D0Elam("x", ast.D0Elet(
                "y_1", ast.D0Evar("x"),
                ast.D0Efix("f", "n", ast.D0Epair(ast.D0Evar("n"), ast.D0Evar("free"))),
            )),
            frozenset({"x", "y_1", "f", "n", "free"}),
        ),
        (ast.D0Efix("x", "x", ast.D0Evar("x")), frozenset({"x"})),
    ]


def scoped_rename_cases():
    """Rename free x occurrences to globally fresh x_1 within each region."""
    return [
        (ast.D0Eint(5), ast.D0Eint(5)),
        (ast.D0Ebtf(False), ast.D0Ebtf(False)),
        (ast.D0Evar("x"), ast.D0Evar("x_1")),
        (ast.D0Evar("y"), ast.D0Evar("y")),
        (ast.D0Eop1("+1", ast.D0Evar("x")), ast.D0Eop1("+1", ast.D0Evar("x_1"))),
        (ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y")), ast.D0Eop2("+", ast.D0Evar("x_1"), ast.D0Evar("y"))),
        (ast.D0Elam("y", ast.D0Evar("x")), ast.D0Elam("y", ast.D0Evar("x_1"))),
        (ast.D0Elam("x", ast.D0Evar("x")), ast.D0Elam("x", ast.D0Evar("x"))),
        (
            ast.D0Efix("f", "n", ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("x"))),
            ast.D0Efix("f", "n", ast.D0Eapp(ast.D0Evar("f"), ast.D0Evar("x_1"))),
        ),
        (ast.D0Efix("x", "n", ast.D0Evar("x")), ast.D0Efix("x", "n", ast.D0Evar("x"))),
        (ast.D0Efix("f", "x", ast.D0Evar("x")), ast.D0Efix("f", "x", ast.D0Evar("x"))),
        (ast.D0Efix("x", "x", ast.D0Evar("x")), ast.D0Efix("x", "x", ast.D0Evar("x"))),
        (ast.D0Eapp(ast.D0Evar("x"), ast.D0Evar("x")), ast.D0Eapp(ast.D0Evar("x_1"), ast.D0Evar("x_1"))),
        (
            ast.D0Eif0(ast.D0Evar("x"), ast.D0Evar("x"), ast.D0Evar("x")),
            ast.D0Eif0(ast.D0Evar("x_1"), ast.D0Evar("x_1"), ast.D0Evar("x_1")),
        ),
        (
            ast.D0Elet("y", ast.D0Evar("x"), ast.D0Evar("x")),
            ast.D0Elet("y", ast.D0Evar("x_1"), ast.D0Evar("x_1")),
        ),
        (
            ast.D0Elet("x", ast.D0Evar("x"), ast.D0Evar("x")),
            ast.D0Elet("x", ast.D0Evar("x_1"), ast.D0Evar("x")),
        ),
        (
            ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("y")),
            ast.D0Epair(ast.D0Evar("x_1"), ast.D0Evar("y")),
        ),
        (ast.D0Epfst(ast.D0Evar("x")), ast.D0Epfst(ast.D0Evar("x_1"))),
        (ast.D0Epsnd(ast.D0Evar("x")), ast.D0Epsnd(ast.D0Evar("x_1"))),
        (
            ast.D0Epair(ast.D0Evar("x"), ast.D0Elam("x", ast.D0Evar("x"))),
            ast.D0Epair(ast.D0Evar("x_1"), ast.D0Elam("x", ast.D0Evar("x"))),
        ),
        (
            ast.D0Elam("y", ast.D0Elet(
                "x", ast.D0Eop1("+1", ast.D0Evar("x")),
                ast.D0Elam("z", ast.D0Evar("x")),
            )),
            ast.D0Elam("y", ast.D0Elet(
                "x", ast.D0Eop1("+1", ast.D0Evar("x_1")),
                ast.D0Elam("z", ast.D0Evar("x")),
            )),
        ),
    ]
