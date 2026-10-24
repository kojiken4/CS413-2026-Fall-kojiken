"""Run all required demonstrations: python -B -m MySolution.demo."""

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .compiler import compile_expr
from .evaluator import EvaluationResult, evaluate
from .examples import DemoCase, build_examples
from .observers import DecodedValue, ObservationResult, observe
from .source_ast import ast
from .source_ops import pretty_source
from .target import Term, pretty


DEFAULT_BUDGET = 10000


def _source_data(value: ast.d0val) -> DecodedValue:
    if isinstance(value, (ast.D0Vint, ast.D0Vbtf)):
        return value.arg1
    if isinstance(value, ast.D0Vpair):
        return _source_data(value.arg1), _source_data(value.arg2)
    raise ValueError("demonstrations must return natural, boolean, or pair data")


def _same_data(left: DecodedValue, right: DecodedValue) -> bool:
    """Keep booleans distinct from integers, including within nested pairs."""
    if type(left) is not type(right):
        return False
    if isinstance(left, tuple):
        return all(_same_data(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def _display(value: DecodedValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, tuple):
        return f"({_display(value[0])}, {_display(value[1])})"
    return str(value)


@dataclass(frozen=True, slots=True)
class DemoResult:
    case: DemoCase
    target: Term
    source_answer: DecodedValue | None
    execution: EvaluationResult
    observation: ObservationResult | None

    @property
    def passed(self) -> bool:
        if self.case.expected is None:
            return self.execution.status == "exhausted" and self.observation is None
        return (
            self.execution.status == "completed"
            and self.observation is not None
            and self.observation.status == "completed"
            and _same_data(self.source_answer, self.case.expected)
            and _same_data(self.observation.value, self.case.expected)
            and _same_data(self.source_answer, self.observation.value)
        )


def run_example(case: DemoCase, *, execution_budget: int, observation_budget: int) -> DemoResult:
    """Run a curated case; never source-evaluate cases marked for exhaustion.

The expected answer is used only for comparison. Both budgets are validated
before starting any evaluation, including when observation will be skipped.
"""
    for budget in (execution_budget, observation_budget):
        if isinstance(budget, bool) or not isinstance(budget, int):
            raise TypeError("demonstration budgets must be integers")
        if budget < 0:
            raise ValueError("demonstration budgets must be nonnegative")
    target = compile_expr(case.source)
    source_answer = None
    if case.expected is not None:
        source_answer = _source_data(evaluate(case.source).value)
    execution = evaluate(target, max_steps=execution_budget)
    observation = None
    if execution.status == "completed" and case.kind is not None:
        observation = observe(execution.value, case.kind, max_steps=observation_budget)
    return DemoResult(case, target, source_answer, execution, observation)


def _report(result: DemoResult, term_file: Path, observation_budget: int) -> None:
    print(f"{result.case.identifier}: {result.case.title}")
    print(f"  Source: {pretty_source(result.case.source)}")
    print(f"  Generated pure term: {term_file.resolve()}")
    execution = result.execution
    print(f"  Execution: {execution.status}; steps={execution.steps}; budget={execution.budget}")
    if result.observation is None:
        reason = "execution did not complete" if execution.status == "exhausted" else "no data kind"
        print(f"  Observation: skipped ({reason}); steps=0; budget={observation_budget}")
        print("  Decoded answer: unavailable")
    else:
        observation = result.observation
        print(f"  Observation: {observation.status}; steps={observation.steps}; budget={observation.budget}")
        answer = _display(observation.value) if observation.status == "completed" else "unavailable"
        print(f"  Decoded answer: {answer}")
        if observation.diagnostic:
            print(f"  Observation diagnostic: {observation.diagnostic}")
    expected = "execution budget exhaustion" if result.case.expected is None else _display(result.case.expected)
    print(f"  Expected answer: {expected}")
    if result.source_answer is None:
        print("  Source evaluation: skipped (expected divergent case)")
    else:
        print(f"  Source answer: {_display(result.source_answer)}")
    print(f"  Check: {'PASS' if result.passed else 'FAIL'}")
    print()


def _nonnegative(value: str) -> int:
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("budget must be a nonnegative integer") from error
    if number < 0:
        raise argparse.ArgumentTypeError("budget must be a nonnegative integer")
    return number


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile, execute, and observe all 14 required examples.")
    parser.add_argument("--execution-budget", type=_nonnegative, default=DEFAULT_BUDGET,
                        help="beta-value steps per program (default: 10000)")
    parser.add_argument("--observation-budget", type=_nonnegative, default=DEFAULT_BUDGET,
                        help="separate beta-value steps per observation (default: 10000)")
    parser.add_argument("--output-dir", type=Path, default=Path("MySolution/demo-output"),
                        help="directory for expanded target terms (default: MySolution/demo-output)")
    options = parser.parse_args(argv)
    print("Execution and observation use independent beta-value step budgets.")
    print("Budget exhaustion does not prove nontermination.\n")
    passed = 0
    examples = build_examples()
    try:
        options.output_dir.mkdir(parents=True, exist_ok=True)
        for case in examples:
            result = run_example(case, execution_budget=options.execution_budget,
                                 observation_budget=options.observation_budget)
            term_file = options.output_dir / f"{case.identifier}.lambda.txt"
            term_file.write_text(pretty(result.target) + "\n", encoding="utf-8")
            _report(result, term_file, options.observation_budget)
            passed += result.passed
    except OSError as error:
        parser.exit(2, f"demo: cannot write generated terms: {error}\n")
    print(f"Summary: {passed}/{len(examples)} demonstrations passed.")
    return 0 if passed == len(examples) else 1


if __name__ == "__main__":
    raise SystemExit(main())
