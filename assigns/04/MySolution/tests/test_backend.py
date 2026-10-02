"""Real language integration, lexical scope, and adapter outcome tests."""

from pathlib import Path

import pytest

from lambda_web import backend as backend_module
from lambda_web import lambda1 as language
from lambda_web.backend import LambdaBackend
from lambda_web.constructor_reader import read_constructor
from lambda_web.contracts import GeneratedArtifact, Operation, Outcome

SAMPLES = Path(__file__).resolve().parents[1] / "samples"


@pytest.fixture
def backend():
    return LambdaBackend()


@pytest.mark.parametrize("source, expected", [
    ('D0Eint(1)', set()),
    ('D0Ebtf(True)', set()),
    ('D0Evar("x")', {"x"}),
    ('D0Eop1("+1", D0Evar("x"))', {"x"}),
    ('D0Eop2("+", D0Evar("x"), D0Evar("y"))', {"x", "y"}),
    ('D0Elam("x", D0Epair(D0Evar("x"), D0Evar("y")))', {"y"}),
    ('D0Efix("f", "x", D0Epair(D0Eapp(D0Evar("f"), D0Evar("x")), D0Evar("y")))', {"y"}),
    ('D0Eapp(D0Evar("f"), D0Evar("x"))', {"f", "x"}),
    ('D0Eif0(D0Evar("c"), D0Evar("a"), D0Evar("b"))', {"c", "a", "b"}),
    ('D0Elet("x", D0Evar("x"), D0Evar("x"))', {"x"}),
    ('D0Epair(D0Evar("x"), D0Evar("x"))', {"x"}),
    ('D0Epfst(D0Epair(D0Evar("x"), D0Evar("y")))', {"x", "y"}),
    ('D0Epsnd(D0Epair(D0Evar("x"), D0Evar("y")))', {"x", "y"}),
    ('D0Elam("x", D0Elam("x", D0Evar("x")))', set()),
    ('D0Elam("x", D0Elet("x", D0Evar("x"), D0Evar("x")))', set()),
    ('D0Elet("x", D0Eint(1), D0Elam("y", D0Epair(D0Evar("x"), D0Evar("y"))))', set()),
    ('D0Elet("unused", D0Eint(1), D0Eint(2))', set()),
    ('D0Eif0(D0Ebtf(True), D0Eint(1), D0Evar("unreachable"))', {"unreachable"}),
])
def test_real_free_variables_every_constructor_and_scope(backend, source, expected):
    variables = language.d0exp_fvset(read_constructor(source))
    assert isinstance(variables, frozenset)
    assert variables == frozenset(expected)
    result = backend.lint(source, 7)
    assert result.operation is Operation.LINT
    assert result.source_revision == 7
    assert isinstance(result.free_variables, frozenset)
    assert result.free_variables == variables
    assert result.outcome is (Outcome.LANGUAGE_ERROR if expected else Outcome.SUCCESS)


def test_undeclared_names_are_sorted_and_deduplicated(backend):
    result = backend.lint('D0Epair(D0Evar("z"), D0Epair(D0Evar("a"), D0Evar("z")))', 2)
    assert result.output == "Undeclared variables: 'a', 'z'"


def test_lint_never_evaluates(backend, monkeypatch):
    def forbidden(*args):
        raise AssertionError("Lint must not evaluate")
    monkeypatch.setattr(language, "d0exp_evaluate", forbidden)
    result = backend.lint((SAMPLES / "division-by-zero.txt").read_text(), 3)
    assert result.outcome is Outcome.SUCCESS
    assert result.output == "No free variables were found."


@pytest.mark.parametrize("source, expected", [
    ('D0Eop2("+", D0Eint(20), D0Eint(22))', 'D0Vint(arg1=42)'),
    ('D0Eop2("-", D0Eint(8), D0Eint(3))', 'D0Vint(arg1=5)'),
    ('D0Eop2("*", D0Eint(6), D0Eint(7))', 'D0Vint(arg1=42)'),
    ('D0Eop2("/", D0Eint(7), D0Eint(2))', 'D0Vint(arg1=3)'),
    ('D0Eop1("+1", D0Eint(1))', 'D0Vint(arg1=2)'),
    ('D0Eop1("-1", D0Eint(1))', 'D0Vint(arg1=0)'),
    ('D0Ebtf(True)', 'D0Vbtf(arg1=True)'),
    ('D0Eif0(D0Ebtf(False), D0Eint(1), D0Eint(2))', 'D0Vint(arg1=2)'),
    ('D0Elet("x", D0Eint(2), D0Evar("x"))', 'D0Vint(arg1=2)'),
    ('D0Eapp(D0Elam("x", D0Evar("x")), D0Eint(9))', 'D0Vint(arg1=9)'),
    ('D0Epfst(D0Epair(D0Eint(1), D0Eint(2)))', 'D0Vint(arg1=1)'),
    ('D0Epsnd(D0Epair(D0Eint(1), D0Eint(2)))', 'D0Vint(arg1=2)'),
    ('D0Epair(D0Eint(1), D0Ebtf(False))', 'D0Vpair(arg1=D0Vint(arg1=1), arg2=D0Vbtf(arg1=False))'),
])
def test_real_interpretation(backend, source, expected):
    result = backend.interpret(source, 9)
    assert result.operation is Operation.INTERPRET
    assert result.source_revision == 9
    assert result.outcome is Outcome.SUCCESS
    assert result.output == expected
    assert result.artifact is None


@pytest.mark.parametrize("filename, default, cases", [
    ('factorial.txt', 5, [(0, 1), (1, 1), (5, 120)]),
    ('fibonacci.txt', 6, [(0, 0), (1, 1), (6, 8)]),
])
def test_real_recursive_samples_and_base_cases(backend, filename, default, cases):
    source = (SAMPLES / filename).read_text(encoding="utf-8")
    for argument, expected in cases:
        modified = source.rsplit(f'D0Eint({default})', 1)
        case_source = f'D0Eint({argument})'.join(modified)
        assert backend.lint(case_source, 1).outcome is Outcome.SUCCESS
        result = backend.interpret(case_source, 1)
        assert result.outcome is Outcome.SUCCESS
        assert result.output == f"D0Vint(arg1={expected})"


@pytest.mark.parametrize("source", [
    'D0Eint()', 'D0Eint(', 'D0Eint(True)', '', 'import os',
])
@pytest.mark.parametrize("operation", ['lint', 'interpret'])
def test_input_errors_are_distinct_from_runtime(backend, source, operation):
    result = getattr(backend, operation)(source, 11)
    assert result.outcome is Outcome.INVALID_INPUT
    assert result.operation.value == operation
    assert result.source_revision == 11
    assert result.output


@pytest.mark.parametrize("source, diagnostic", [
    ('D0Eop2("/", D0Eint(1), D0Eint(0))', 'ZeroDivisionError'),
    ('D0Eop2("+", D0Ebtf(True), D0Eint(1))', 'TypeError'),
    ('D0Eop1("unknown", D0Eint(1))', 'not supported'),
    ('D0Epfst(D0Eint(1))', 'D0Vpair'),
    ('D0Eapp(D0Eint(1), D0Eint(2))', 'not D0Vlam/D0Vfix'),
])
def test_closed_runtime_failures(backend, source, diagnostic):
    assert backend.lint(source, 4).outcome is Outcome.SUCCESS
    result = backend.interpret(source, 4)
    assert result.outcome is Outcome.RUNTIME_ERROR
    assert diagnostic in result.output


@pytest.mark.parametrize("source", [
    'D0Evar("x")',
    'D0Epair(D0Evar("x"), D0Eint(1))',
    'D0Epair(D0Eint(1), D0Epair(D0Eint(2), D0Evar("x")))',
])
def test_error_sentinels_directly_or_inside_pairs(backend, source):
    result = backend.interpret(source, 5)
    assert result.outcome is Outcome.RUNTIME_ERROR
    assert 'D0V000()' in result.output


def test_interpret_is_independent_of_lint_and_uses_empty_environment(backend, monkeypatch):
    real_evaluate = language.d0exp_evaluate
    environments = []
    def forbidden_lint(*args):
        raise AssertionError("Interpret must not require Lint")
    def evaluate(expression, environment):
        environments.append(environment)
        return real_evaluate(expression, environment)
    monkeypatch.setattr(language, 'd0exp_fvset', forbidden_lint)
    monkeypatch.setattr(language, 'd0exp_evaluate', evaluate)
    assert backend.interpret('D0Eint(1)', 3).outcome is Outcome.SUCCESS
    assert environments == [language.ENVnil()]


@pytest.mark.parametrize("method, tool", [
    ('lint', 'd0exp_fvset'), ('interpret', 'd0exp_evaluate'),
])
def test_unexpected_failures_are_backend_failures_and_allow_retry(backend, monkeypatch, method, tool):
    real_tool = getattr(language, tool)
    def fail(*args):
        raise RuntimeError('injected tool failure')
    monkeypatch.setattr(language, tool, fail)
    result = getattr(backend, method)('D0Eint(1)', 6)
    assert result.outcome is Outcome.BACKEND_FAILURE
    assert result.source_revision == 6
    assert 'injected tool failure' in result.output
    monkeypatch.setattr(language, tool, real_tool)
    assert getattr(backend, method)('D0Eint(1)', 6).outcome is Outcome.SUCCESS


def test_unexpected_reader_failure_is_backend_failure(backend, monkeypatch):
    def fail(*args):
        raise RuntimeError('reader failed')
    monkeypatch.setattr(backend_module, 'read_constructor', fail)
    assert backend.lint('D0Eint(1)', 1).outcome is Outcome.BACKEND_FAILURE


@pytest.mark.parametrize("method, tool, value", [
    ('lint', 'd0exp_fvset', {'x'}),
    ('lint', 'd0exp_fvset', frozenset({1})),
    ('interpret', 'd0exp_evaluate', None),
])
def test_invalid_tool_returns_are_backend_failures(backend, monkeypatch, method, tool, value):
    monkeypatch.setattr(language, tool, lambda *args: value)
    assert getattr(backend, method)('D0Eint(1)', 1).outcome is Outcome.BACKEND_FAILURE


@pytest.mark.parametrize("method, expected", [
    ('typecheck', Operation.TYPECHECK), ('compile', Operation.COMPILE),
])
def test_placeholders_do_not_parse_or_run_tools(backend, monkeypatch, method, expected):
    def forbidden(*args):
        raise AssertionError('Placeholder must not claim analysis')
    monkeypatch.setattr(backend_module, 'read_constructor', forbidden)
    result = getattr(backend, method)('malformed source', 12)
    assert result.operation is expected
    assert result.source_revision == 12
    assert result.outcome is Outcome.NOT_IMPLEMENTED
    assert 'not yet implemented' in result.output
    assert result.artifact is None


@pytest.mark.parametrize("artifact", [None, GeneratedArtifact(12, 'future code', 'future format')])
def test_execute_never_substitutes_interpretation_or_compilation(backend, monkeypatch, artifact):
    def forbidden(*args):
        raise AssertionError('Execute must not interpret or compile')
    monkeypatch.setattr(backend, 'interpret', forbidden)
    monkeypatch.setattr(backend, 'compile', forbidden)
    result = backend.execute(artifact, 12)
    assert result.operation is Operation.EXECUTE
    assert result.source_revision == 12
    assert result.outcome is Outcome.UNAVAILABLE
    assert 'generated code' in result.output
    assert result.artifact is None


@pytest.mark.parametrize("filename, lint_outcome, interpret_outcome", [
    ('open-variable.txt', Outcome.LANGUAGE_ERROR, Outcome.RUNTIME_ERROR),
    ('division-by-zero.txt', Outcome.SUCCESS, Outcome.RUNTIME_ERROR),
    ('invalid-input.txt', Outcome.INVALID_INPUT, Outcome.INVALID_INPUT),
])
def test_error_sample_files(backend, filename, lint_outcome, interpret_outcome):
    source = (SAMPLES / filename).read_text(encoding='utf-8')
    assert backend.lint(source, 1).outcome is lint_outcome
    assert backend.interpret(source, 1).outcome is interpret_outcome


@pytest.mark.parametrize("source, prefix", [
    ('D0Elam("x", D0Evar("x"))', 'D0Vlam('),
    ('D0Efix("f", "x", D0Evar("x"))', 'D0Vfix('),
])
def test_closure_values_are_not_error_sentinels(backend, source, prefix):
    result = backend.interpret(source, 2)
    assert result.outcome is Outcome.SUCCESS
    assert result.output.startswith(prefix)


def test_evaluator_recursion_error_is_runtime_failure(backend, monkeypatch):
    def fail(*args):
        raise RecursionError('recursion limit reached')
    monkeypatch.setattr(language, 'd0exp_evaluate', fail)
    result = backend.interpret('D0Eint(1)', 3)
    assert result.outcome is Outcome.RUNTIME_ERROR
    assert 'RecursionError' in result.output
