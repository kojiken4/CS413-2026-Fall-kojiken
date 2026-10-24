"""Constructor-built source examples, ordered by REQUIREMENTS.md DEMO IDs.

No compilation or execution happens on import. Expected answers are test oracles,
never inputs to compilation, target evaluation, or observation.
"""

from dataclasses import dataclass

from .observers import DecodedValue, ExpectedKind
from .source_ast import ast


@dataclass(frozen=True, slots=True)
class DemoCase:
    identifier: str
    title: str
    source: ast.d0exp
    kind: ExpectedKind | None
    expected: DecodedValue | None  # None denotes expected execution exhaustion.


def loop() -> ast.d0exp:
    return ast.D0Eapp(
        ast.D0Efix("loop", "x", ast.D0Eapp(ast.D0Evar("loop"), ast.D0Evar("x"))),
        ast.D0Eint(0),
    )


def factorial() -> ast.D0Efix:
    return ast.D0Efix(
        "fact", "n",
        ast.D0Eif0(
            ast.D0Eop2("==", ast.D0Evar("n"), ast.D0Eint(0)),
            ast.D0Eint(1),
            ast.D0Eop2("*", ast.D0Evar("n"), ast.D0Eapp(
                ast.D0Evar("fact"),
                ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1)),
            )),
        ),
    )


def fibonacci() -> ast.D0Efix:
    return ast.D0Efix(
        "fib", "n",
        ast.D0Eif0(
            ast.D0Eop2("<=", ast.D0Evar("n"), ast.D0Eint(1)),
            ast.D0Evar("n"),
            ast.D0Eop2("+",
                ast.D0Eapp(ast.D0Evar("fib"),
                          ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1))),
                ast.D0Eapp(ast.D0Evar("fib"),
                          ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(2))),
            ),
        ),
    )


def build_examples() -> tuple[DemoCase, ...]:
    """Return fresh source ASTs for all 14 required cases, including both loops."""
    return (
        DemoCase("DEMO-01", "2 + 3 * 4", ast.D0Eop2("+", ast.D0Eint(2),
            ast.D0Eop2("*", ast.D0Eint(3), ast.D0Eint(4))), "natural", 14),
        DemoCase("DEMO-02", "2 - 5", ast.D0Eop2("-", ast.D0Eint(2), ast.D0Eint(5)),
                 "natural", 0),
        DemoCase("DEMO-03", "if 2 <= 3 then 7 else 9", ast.D0Eif0(
            ast.D0Eop2("<=", ast.D0Eint(2), ast.D0Eint(3)), ast.D0Eint(7), ast.D0Eint(9)),
                 "natural", 7),
        DemoCase("DEMO-04", "let x = 3 in (lam y. x + y) 4", ast.D0Elet(
            "x", ast.D0Eint(3), ast.D0Eapp(ast.D0Elam("y",
                ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))), ast.D0Eint(4))),
                 "natural", 7),
        DemoCase("DEMO-05", "fst (pair 2 true)",
                 ast.D0Epfst(ast.D0Epair(ast.D0Eint(2), ast.D0Ebtf(True))), "natural", 2),
        DemoCase("DEMO-06", "snd (pair 2 true)",
                 ast.D0Epsnd(ast.D0Epair(ast.D0Eint(2), ast.D0Ebtf(True))), "boolean", True),
        DemoCase("DEMO-07", "(lam f. f 3) (lam x. x + 1)", ast.D0Eapp(
            ast.D0Elam("f", ast.D0Eapp(ast.D0Evar("f"), ast.D0Eint(3))),
            ast.D0Elam("x", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Eint(1)))), "natural", 4),
        DemoCase("DEMO-08", "if true then 1 else LOOP",
                 ast.D0Eif0(ast.D0Ebtf(True), ast.D0Eint(1), loop()), "natural", 1),
        DemoCase("DEMO-09", "(lam x. 0) LOOP",
                 ast.D0Eapp(ast.D0Elam("x", ast.D0Eint(0)), loop()), None, None),
        DemoCase("DEMO-10", "factorial 4", ast.D0Eapp(factorial(), ast.D0Eint(4)),
                 "natural", 24),
        DemoCase("DEMO-11", "Fibonacci 5", ast.D0Eapp(fibonacci(), ast.D0Eint(5)),
                 "natural", 5),
        DemoCase("DEMO-12", "LOOP", loop(), None, None),
        DemoCase("DEMO-13", "true and false",
                 ast.D0Eop2("and", ast.D0Ebtf(True), ast.D0Ebtf(False)), "boolean", False),
        DemoCase("DEMO-14", "false or true",
                 ast.D0Eop2("or", ast.D0Ebtf(False), ast.D0Ebtf(True)), "boolean", True),
    )
