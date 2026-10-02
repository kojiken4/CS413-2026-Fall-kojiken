"""Acceptance and rejection tests for the restricted constructor reader."""

import ast
import builtins
from dataclasses import fields

import pytest

from lambda_web import lambda1 as language
from lambda_web.constructor_reader import (
    ConstructorInputError,
    MAX_SOURCE_BYTES,
    read_constructor,
    validate_source,
)


CASES = [
    ('D0Eint(42)', language.D0Eint(42)),
    ('D0Ebtf(True)', language.D0Ebtf(True)),
    ('D0Evar("x")', language.D0Evar("x")),
    ('D0Eop1("-1", D0Eint(2))', language.D0Eop1("-1", language.D0Eint(2))),
    ('D0Eop2("+", D0Eint(20), D0Eint(22))', language.D0Eop2("+", language.D0Eint(20), language.D0Eint(22))),
    ('D0Elam("x", D0Evar("x"))', language.D0Elam("x", language.D0Evar("x"))),
    ('D0Efix("f", "x", D0Evar("x"))', language.D0Efix("f", "x", language.D0Evar("x"))),
    ('D0Eapp(D0Elam("x", D0Evar("x")), D0Eint(2))', language.D0Eapp(language.D0Elam("x", language.D0Evar("x")), language.D0Eint(2))),
    ('D0Eif0(D0Ebtf(True), D0Eint(1), D0Eint(2))', language.D0Eif0(language.D0Ebtf(True), language.D0Eint(1), language.D0Eint(2))),
    ('D0Elet("x", D0Eint(2), D0Evar("x"))', language.D0Elet("x", language.D0Eint(2), language.D0Evar("x"))),
    ('D0Epair(D0Eint(1), D0Eint(2))', language.D0Epair(language.D0Eint(1), language.D0Eint(2))),
    ('D0Epfst(D0Epair(D0Eint(1), D0Eint(2)))', language.D0Epfst(language.D0Epair(language.D0Eint(1), language.D0Eint(2)))),
    ('D0Epsnd(D0Epair(D0Eint(1), D0Eint(2)))', language.D0Epsnd(language.D0Epair(language.D0Eint(1), language.D0Eint(2)))),
]


@pytest.mark.parametrize("source, expected", CASES)
def test_every_constructor_positional(source, expected):
    assert read_constructor(source) == expected


@pytest.mark.parametrize("source, expected", CASES)
def test_every_constructor_named(source, expected):
    # The outer call is rewritten using the supplied dataclass's field names.
    tree = ast.parse(source, mode="eval").body
    named = ', '.join(
        f"{field.name}={ast.unparse(argument)}"
        for field, argument in zip(fields(expected), tree.args)
    )
    assert read_constructor(f"{type(expected).__name__}({named})") == expected


@pytest.mark.parametrize("source, value", [
    ('D0Eint(-42)', -42), ('D0Eint(+42)', 42), ('D0Eint(-0)', 0),
    ('D0Eint(0xff)', 255), ('D0Eint(1_000)', 1000),
])
def test_integer_literals(source, value):
    assert read_constructor(source) == language.D0Eint(value)


def test_comments_multiline_and_keyword_order():
    source = """  # A nested constructor expression
D0Eop2(
    "+", # operator
    arg2=D0Eint(22),
    arg1=D0Eint(20),
) # trailing comment
"""
    assert read_constructor(source) == language.D0Eop2("+", language.D0Eint(20), language.D0Eint(22))


def test_literal_strings_unicode_and_booleans():
    value = "<script>\u00e9</script>\n"
    assert read_constructor(f"D0Evar({value!r})") == language.D0Evar(value)
    assert read_constructor('D0Ebtf(False)') == language.D0Ebtf(False)


@pytest.mark.parametrize("source, message", [
    ('D0Eint()', 'Missing arguments'),
    ('D0Eint(1, 2)', 'expects 1 arguments'),
    ('D0Eint(other=1)', 'Unknown argument'),
    ('D0Eint(1, arg1=2)', 'Duplicate argument'),
    ('D0Eint(arg1=1, arg1=2)', 'Duplicate argument'),
    ('D0Eint(*[1])', 'expansion'),
    ('D0Eint(**{"arg1": 1})', 'expansion'),
    ('D0Eint(True)', 'int literal'),
    ('D0Eint(1.0)', 'int literal'),
    ('D0Eint("1")', 'int literal'),
    ('D0Eint(-True)', 'int literal'),
    ('D0Eint(--1)', 'int literal'),
    ('D0Ebtf(1)', 'bool literal'),
    ('D0Evar(1)', 'str literal'),
    ('D0Eop2(1, D0Eint(1), D0Eint(2))', 'str literal'),
    ('D0Elam(D0Evar("x"), D0Eint(1))', 'str literal'),
    ('D0Efix("f", 1, D0Eint(1))', 'str literal'),
    ('D0Epair(D0Eint(1), 2)', 'constructor call'),
    ('D0Eif0(True, D0Eint(1), D0Eint(2))', 'constructor call'),
    ('D0E000()', 'Unsupported constructor'),
    ('D0Vint(1)', 'Unsupported constructor'),
    ('ENVnil()', 'Unsupported constructor'),
    ('Unknown(1)', 'Unsupported constructor'),
])
def test_invalid_arguments_and_constructors(source, message):
    with pytest.raises(ConstructorInputError, match=message):
        read_constructor(source)


@pytest.mark.parametrize("source", [
    '42', 'True', '"hello"', 'D0Eint', 'x',
    'import os', 'x = D0Eint(1)', 'D0Eint(1); D0Eint(2)',
    'D0Eint(', 'D0Eint(1)\nD0Eint(2)', '# only a comment', '\x00',
    'lambda1.D0Eint(1)', 'D0Eint(1).arg1',
    '__import__("os").system("echo unwanted")',
    'eval("D0Eint(1)")', 'exec("x = 1")', 'open("unwanted", "w")',
    'D0Eint(1 + 2)', 'D0Eint(abs(-1))', 'D0Eint(x)',
    '[D0Eint(1)]', '{"x": D0Eint(1)}', '(D0Eint(1),)',
    '[D0Eint(x) for x in range(2)]',
    'D0Eint(1) if True else D0Eint(2)', '(x := D0Eint(1))',
    'D0Evar(f"{1}")', 'D0Evar(b"x")', 'D0Evar(None)',
    'D0Eint([1][0])', 'D0Eint(True and 1)',
])
def test_python_outside_constructor_format_is_rejected(source):
    with pytest.raises(ConstructorInputError):
        read_constructor(source)


def test_reader_does_not_evaluate_or_execute(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("Reader must not execute source or evaluate LAMBDA")
    monkeypatch.setattr(builtins, "eval", forbidden)
    monkeypatch.setattr(builtins, "exec", forbidden)
    monkeypatch.setattr(language, "d0exp_evaluate", forbidden)
    assert read_constructor('D0Eop2("/", D0Eint(1), D0Eint(0))') == language.D0Eop2("/", language.D0Eint(1), language.D0Eint(0))
    marker = tmp_path / "executed.txt"
    with pytest.raises(ConstructorInputError):
        read_constructor(f'open({str(marker)!r}, "w").write("executed")')
    assert not marker.exists()


@pytest.mark.parametrize("source", ['', ' ', '\t\r\n'])
def test_empty_source_rejected(source):
    with pytest.raises(ConstructorInputError, match='empty'):
        read_constructor(source)


def test_utf8_byte_limit_before_stripping():
    base = 'D0Eint(1)'
    source = base + ' ' * (MAX_SOURCE_BYTES - len(base))
    assert read_constructor(source) == language.D0Eint(1)
    with pytest.raises(ConstructorInputError, match='65536-byte'):
        read_constructor(source + ' ')
    prefix = 'D0Evar("'
    suffix = '")'
    unicode_source = prefix + 'é' * ((MAX_SOURCE_BYTES - len(prefix + suffix)) // 2) + suffix
    validate_source(unicode_source)
    with pytest.raises(ConstructorInputError, match='65536-byte'):
        validate_source(unicode_source + 'é')


@pytest.mark.parametrize("source", [None, b'D0Eint(1)', 42])
def test_non_text_rejected(source):
    with pytest.raises(ConstructorInputError, match='text'):
        read_constructor(source)


def test_invalid_unicode_rejected():
    with pytest.raises(ConstructorInputError, match='UTF-8'):
        read_constructor('D0Evar("\ud800")')


def test_deep_input_has_input_diagnostic():
    source = 'D0Epfst(' * 300 + 'D0Eint(1)' + ')' * 300
    with pytest.raises(ConstructorInputError):
        read_constructor(source)


def test_size_validation_does_not_parse_source():
    # Applying malformed source must remain possible; tools diagnose its syntax.
    validate_source('not valid constructor syntax')


def test_unknown_operator_is_left_to_language_tools():
    assert read_constructor('D0Eop1("unknown", D0Eint(1))') == language.D0Eop1("unknown", language.D0Eint(1))


@pytest.mark.parametrize("source, expected", CASES)
def test_every_constructor_rejects_missing_and_extra_arguments(source, expected):
    tree = ast.parse(source, mode="eval").body
    original_arguments = list(tree.args)
    tree.args = original_arguments[:-1]
    with pytest.raises(ConstructorInputError, match="Missing arguments"):
        read_constructor(ast.unparse(tree))
    tree.args = original_arguments + [ast.Constant(value=0)]
    with pytest.raises(ConstructorInputError, match="expects"):
        read_constructor(ast.unparse(tree))


@pytest.mark.parametrize("source, expected", CASES)
def test_every_constructor_rejects_wrong_field_types(source, expected):
    for index, field in enumerate(fields(expected)):
        tree = ast.parse(source, mode="eval").body
        value = getattr(expected, field.name)
        wrong_value = True if type(value) is int else 0
        tree.args[index] = ast.Constant(value=wrong_value)
        with pytest.raises(ConstructorInputError):
            read_constructor(ast.unparse(tree))
