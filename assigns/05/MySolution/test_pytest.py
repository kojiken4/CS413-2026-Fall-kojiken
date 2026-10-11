"""Independent pytest-style suite; run from the assignment directory."""

from copy import deepcopy
from unittest.mock import patch

import pytest

import lambda1_vp as ast
from MySolution import operations
from MySolution.helper_cases import all_names_cases, scoped_rename_cases
from MySolution.substitution_cases import constructor_substitution_cases, binding_substitution_cases


def test_solution_module_imports():
    assert operations.__name__ == "MySolution.operations"


def test_supplied_ast_dispatches_to_visitor():
    expression = ast.D0Elam(
        "x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))
    )
    assert expression.accept(ast.FreeVariableVisitor()) == frozenset({"y"})


@pytest.mark.parametrize("expression, expected", [
    (ast.D0Eint(0), "0"),
    (ast.D0Eint(-7), "-7"),
    (ast.D0Eint(123456789012345678901234567890), "123456789012345678901234567890"),
    (ast.D0Ebtf(True), "true"),
    (ast.D0Ebtf(False), "false"),
    (ast.D0Evar("_value2"), "_value2"),
    (ast.D0Eop1("+1", ast.D0Evar("x")), "(+1 x)"),
    (ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)), "(x + 1)"),
    (ast.D0Elam("x", ast.D0Evar("x")), "(lam x. x)"),
    (ast.D0Efix("f", "n", ast.D0Evar("n")), "(fix f(n). n)"),
    (ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(4)), "(f 4)"),
    (ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), ast.D0Eint(2)), "(if true then 1 else 2)"),
    (ast.D0Elet("x", ast.D0Eint(3), ast.D0Evar("x")), "(let x = 3 in x)"),
    (ast.D0Epair(ast.D0Eint(1), ast.D0Eint(2)), "(pair 1 2)"),
    (ast.D0Epfst(ast.D0Evar("p")), "(fst p)"),
    (ast.D0Epsnd(ast.D0Evar("p")), "(snd p)"),
])
def test_exact_output_for_every_constructor(expression, expected):
    assert operations.d0exp_pretty(expression) == expected
    assert expression.accept(operations.PrettyPrintVisitor()) == expected


def test_nested_application_matches_assignment_example():
    expression = ast.D0Eapp(
        ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))),
        ast.D0Eint(4),
    )
    assert operations.d0exp_pretty(expression) == "((lam x. (x + 1)) 4)"


def test_nested_bindings_and_projections():
    expression = ast.D0Elet(
        "p", ast.D0Epair(ast.D0Eint(-2), ast.D0Ebtf(False)),
        ast.D0Efix("f", "n", ast.D0Eif0(
            ast.D0Epsnd(ast.D0Evar("p")),
            ast.D0Epfst(ast.D0Evar("p")),
            ast.D0Eapp(ast.D0Evar("f"), ast.D0Eop1("-1", ast.D0Evar("n"))),
        )),
    )
    assert operations.d0exp_pretty(expression) == (
        "(let p = (pair -2 false) in (fix f(n). (if (snd p) then (fst p) else (f (-1 n)))))"
    )


def test_names_and_operators_are_inserted_literally():
    expression = ast.D0Eop2("custom_op", ast.D0Eop1("neg", ast.D0Evar("_x2")), ast.D0Eint(8))
    assert operations.d0exp_pretty(expression) == "((neg _x2) custom_op 8)"


def test_printing_does_not_evaluate():
    expression = ast.D0Eop2("/", ast.D0Eint(1), ast.D0Eint(0))
    with patch.object(ast.EvaluateVisitor, "visit_op2", side_effect=AssertionError("unexpected evaluation")):
        assert operations.d0exp_pretty(expression) == "(1 / 0)"


def test_printing_preserves_input():
    expression = ast.D0Elam("x", ast.D0Epair(ast.D0Evar("x"), ast.D0Eint(1)))
    snapshot = deepcopy(expression)
    assert operations.d0exp_pretty(expression) == "(lam x. (pair x 1))"
    assert expression == snapshot


@pytest.mark.parametrize("expression, expected", all_names_cases())
def test_all_names_including_unused_binders(expression, expected):
    snapshot = deepcopy(expression)
    assert expression.accept(operations.AllNamesVisitor()) == expected
    assert expression == snapshot


@pytest.mark.parametrize("expression, expected", scoped_rename_cases())
def test_scoped_renaming_and_input_preservation(expression, expected):
    snapshot = deepcopy(expression)
    assert expression.accept(operations.ScopedRenameVisitor("x", "x_1")) == expected
    assert expression == snapshot


def test_helpers_do_not_evaluate():
    expression = ast.D0Eop2("/", ast.D0Evar("x"), ast.D0Eint(0))
    with patch.object(ast.EvaluateVisitor, "visit_op2", side_effect=AssertionError("unexpected evaluation")):
        assert expression.accept(operations.AllNamesVisitor()) == frozenset({"x"})
        assert expression.accept(operations.ScopedRenameVisitor("x", "x_1")) == (
            ast.D0Eop2("/", ast.D0Evar("x_1"), ast.D0Eint(0))
        )


def test_fresh_names_avoid_both_inputs_and_target():
    expression = ast.D0Elam("y_1", ast.D0Evar("x"))
    replacement = ast.D0Elam("y_2", ast.D0Evar("y"))
    target = "y_3"
    reserved = (
        expression.accept(operations.AllNamesVisitor())
        | replacement.accept(operations.AllNamesVisitor())
        | {target}
    )
    generator = operations.FreshNameGenerator(reserved)
    assert generator.fresh("y") == "y_4"
    assert generator.fresh("y") == "y_5"
    assert generator.fresh("f") == "f_6"
    assert reserved == frozenset({"y_1", "x", "y_2", "y", "y_3"})


def test_fresh_names_are_unique_and_deterministic():
    first = operations.FreshNameGenerator(frozenset())
    second = operations.FreshNameGenerator(frozenset())
    expected = ["y_1", "y_2", "f_3", "_x_4"]
    assert [first.fresh(name) for name in ("y", "y", "f", "_x")] == expected
    assert [second.fresh(name) for name in ("y", "y", "f", "_x")] == expected
    assert len(set(expected)) == len(expected)


@pytest.mark.parametrize("expression, expected", constructor_substitution_cases())
def test_substitution_through_every_constructor(expression, expected):
    assert operations.d0exp_substitute(expression, "x", ast.D0Eint(3)) == expected


@pytest.mark.parametrize("expression, target, replacement, expected", binding_substitution_cases())
def test_binding_rules_and_capture_avoidance(expression, target, replacement, expected):
    assert operations.d0exp_substitute(expression, target, replacement) == expected


def test_replacement_is_inserted_once_and_reused_exactly():
    replacement = ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1))
    expression = ast.D0Epair(ast.D0Evar("x"), ast.D0Evar("x"))
    result = operations.d0exp_substitute(expression, "x", replacement)
    assert result == ast.D0Epair(replacement, replacement)
    assert result.arg1 is replacement
    assert result.arg2 is replacement


def test_direct_substitution_visitor_dispatch():
    expression = ast.D0Elam("y", ast.D0Evar("x"))
    replacement = ast.D0Evar("y")
    reserved = expression.accept(operations.AllNamesVisitor()) | replacement.accept(operations.AllNamesVisitor()) | {"x"}
    visitor = operations.SubstitutionVisitor("x", replacement, operations.FreshNameGenerator(reserved))
    assert expression.accept(visitor) == ast.D0Elam("y_1", ast.D0Evar("y"))
