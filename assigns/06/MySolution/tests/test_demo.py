"""Required demonstration acceptance, reporting, and resource failure behavior."""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
from io import StringIO
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from MySolution import demo
from MySolution.compiler import compile_expr
from MySolution.examples import DemoCase, build_examples
from MySolution.observers import ObservationResult
from MySolution.source_ast import ast
from MySolution.target import App, Lam, Var, free_vars, pretty


def temporary_directory():
    # Keep test writes and cleanup inside the solution, including sandboxed runs.
    return TemporaryDirectory(dir=Path(__file__).resolve().parents[1], prefix=".demo-test-")


class DemonstrationTests(unittest.TestCase):
    def test_all_14_required_cases_have_explicit_correct_answers_and_kinds(self) -> None:
        cases = build_examples()
        self.assertEqual([case.identifier for case in cases],
                         [f"DEMO-{number:02}" for number in range(1, 15)])
        self.assertEqual([case.expected for case in cases],
                         [14, 0, 7, 7, 2, True, 4, 1, None, 24, 5, None, False, True])
        self.assertEqual([case.kind for case in cases],
                         ["natural"] * 5 + ["boolean", "natural", "natural", None,
                                             "natural", "natural", None, "boolean", "boolean"])
        # Match syntax independently of labels so a mistaken fixture cannot pass
        # merely because it computes the same expected answer.
        self.assertEqual([demo.pretty_source(case.source) for case in cases], [
            "(2 + (3 * 4))", "(2 - 5)", "(if (2 <= 3) then 7 else 9)",
            "(let x = 3 in ((lam y. (x + y)) 4))", "(fst (pair 2 true))",
            "(snd (pair 2 true))", "((lam f. (f 3)) (lam x. (x + 1)))",
            "(if true then 1 else ((fix loop(x). (loop x)) 0))",
            "((lam x. 0) ((fix loop(x). (loop x)) 0))",
            "((fix fact(n). (if (n == 0) then 1 else (n * (fact (n - 1))))) 4)",
            "((fix fib(n). (if (n <= 1) then n else ((fib (n - 1)) + (fib (n - 2))))) 5)",
            "((fix loop(x). (loop x)) 0)", "(true and false)", "(false or true)",
        ])

    def test_all_required_pipelines_pass_with_closed_pure_output_and_unchanged_source(self) -> None:
        for case in build_examples():
            with self.subTest(identifier=case.identifier):
                before = deepcopy(case.source)
                result = demo.run_example(case, execution_budget=10000, observation_budget=10000)
                self.assertTrue(result.passed)
                self.assertEqual(case.source, before)
                self.assertEqual(free_vars(result.target), frozenset())
                pending = [result.target]
                while pending:
                    term = pending.pop()
                    self.assertIn(type(term), (Var, Lam, App))
                    if isinstance(term, Lam):
                        pending.append(term.body)
                    elif isinstance(term, App):
                        pending.extend((term.fn, term.arg))
                if case.expected is None:
                    self.assertEqual(result.execution.status, "exhausted")
                    self.assertEqual(result.execution.steps, 10000)
                    self.assertIsNone(result.source_answer)
                    self.assertIsNone(result.observation)
                else:
                    self.assertEqual(result.source_answer, case.expected)
                    self.assertEqual(result.observation.value, case.expected)
                    self.assertIs(type(result.observation.value), type(case.expected))

    def test_loop_cases_never_call_source_evaluation_or_observation(self) -> None:
        real_evaluate = demo.evaluate

        def target_only(expression, **kwargs):
            self.assertIsInstance(expression, (Var, Lam, App))
            return real_evaluate(expression, **kwargs)

        with (
            patch.object(demo, "evaluate", side_effect=target_only),
            patch.object(demo, "observe", side_effect=AssertionError("observation of exhaustion")),
        ):
            for case in build_examples():
                if case.expected is None:
                    self.assertTrue(demo.run_example(case, execution_budget=100,
                                                      observation_budget=0).passed)

    def test_expected_answers_are_only_comparisons_not_computation(self) -> None:
        case = replace(build_examples()[0], expected=999)
        result = demo.run_example(case, execution_budget=100, observation_budget=100)
        self.assertEqual(result.source_answer, 14)
        self.assertEqual(result.observation.value, 14)
        self.assertFalse(result.passed)

    def test_booleans_cannot_pass_as_equal_integers(self) -> None:
        result = demo.run_example(build_examples()[1], execution_budget=100, observation_budget=100)
        self.assertTrue(result.passed)
        self.assertFalse(replace(result, source_answer=False).passed)
        self.assertFalse(replace(result, observation=replace(result.observation, value=False)).passed)

    def test_insufficient_execution_skips_observation_and_fails_expected_completion(self) -> None:
        with patch.object(demo, "observe", side_effect=AssertionError("incomplete execution")):
            result = demo.run_example(build_examples()[0], execution_budget=0, observation_budget=100)
        self.assertEqual(result.execution.status, "exhausted")
        self.assertEqual(result.execution.steps, 0)
        self.assertIsNone(result.observation)
        self.assertFalse(result.passed)

    def test_observation_exhaustion_is_independent_and_never_a_decoded_success(self) -> None:
        case = build_examples()[0]
        result = demo.run_example(case, execution_budget=4, observation_budget=0)
        self.assertEqual(result.execution.status, "completed")
        self.assertEqual(result.execution.steps, 4)
        self.assertEqual(result.observation.status, "exhausted")
        self.assertEqual(result.observation.steps, 0)
        self.assertIsNone(result.observation.value)
        self.assertFalse(result.passed)
        exact = demo.run_example(case, execution_budget=4, observation_budget=26)
        self.assertTrue(exact.passed)
        self.assertEqual(exact.observation.steps, 26)

    def test_budgets_are_checked_before_running_any_program(self) -> None:
        with patch.object(demo, "evaluate", side_effect=AssertionError("invalid budget")):
            for bad, exception in ((-1, ValueError), (True, TypeError), (1.5, TypeError)):
                for execution, observation in ((bad, 100), (100, bad)):
                    with self.subTest(execution=execution, observation=observation):
                        with self.assertRaises(exception):
                            demo.run_example(build_examples()[0], execution_budget=execution,
                                             observation_budget=observation)

    def test_fresh_fixtures_are_independent_of_previous_mutation(self) -> None:
        original = build_examples()
        original[0].source.arg1.arg1 = 99
        self.assertEqual(build_examples()[0].source.arg1.arg1, 2)

    def test_cli_runs_all_cases_and_writes_exact_expanded_terms(self) -> None:
        with temporary_directory() as temporary:
            directory = Path(temporary) / "terms with spaces"
            process = subprocess.run(
                [sys.executable, "-B", "-m", "MySolution.demo", "--output-dir", str(directory)],
                cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True,
                timeout=30, check=False,
            )
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(process.stdout.count("Check: PASS"), 14)
            self.assertIn("Summary: 14/14 demonstrations passed.", process.stdout)
            self.assertIn("Observation: skipped (execution did not complete); steps=0; budget=10000",
                          process.stdout)
            self.assertEqual(len(list(directory.iterdir())), 14)
            for case in build_examples():
                file = directory / f"{case.identifier}.lambda.txt"
                self.assertEqual(file.read_text(encoding="utf-8"), pretty(compile_expr(case.source)) + "\n")
                self.assertIn(str(file.resolve()), process.stdout)
            for field in ("Source:", "Execution:", "Observation:", "Decoded answer:", "Expected answer:"):
                self.assertEqual(process.stdout.count(field), 14)
            self.assertEqual(process.stdout.count("Source answer:"), 12)
            self.assertEqual(process.stdout.count("Source evaluation: skipped"), 2)

    def test_cli_small_budgets_report_failures_continue_all_cases_and_exit_one(self) -> None:
        for flag, status in (("--execution-budget", "Execution: exhausted"),
                             ("--observation-budget", "Observation: exhausted")):
            with self.subTest(flag=flag), temporary_directory() as temporary:
                output = StringIO()
                with redirect_stdout(output):
                    code = demo.main([flag, "0", "--output-dir", temporary])
                self.assertEqual(code, 1)
                self.assertIn(status, output.getvalue())
                self.assertIn("Summary: 2/14 demonstrations passed.", output.getvalue())
                self.assertEqual(len(list(Path(temporary).iterdir())), 14)

    def test_cli_rejects_invalid_budgets_without_creating_output(self) -> None:
        for flag in ("--execution-budget", "--observation-budget"):
            for bad in ("-1", "1.5", "no"):
                with self.subTest(flag=flag, bad=bad), temporary_directory() as temporary:
                    directory = Path(temporary) / "uncreated"
                    with redirect_stderr(StringIO()), self.assertRaises(SystemExit) as error:
                        demo.main([flag, bad, "--output-dir", str(directory)])
                    self.assertEqual(error.exception.code, 2)
                    self.assertFalse(directory.exists())

    def test_cli_reports_unwritable_output_as_exit_two(self) -> None:
        with temporary_directory() as temporary:
            file = Path(temporary) / "file.txt"
            file.write_text("keep this content", encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as errors:
                with self.assertRaises(SystemExit) as error:
                    demo.main(["--output-dir", str(file)])
            self.assertEqual(error.exception.code, 2)
            self.assertIn("cannot write generated terms", errors.getvalue())
            self.assertEqual(file.read_text(encoding="utf-8"), "keep this content")

    def test_malformed_observation_is_reported_with_diagnostic_and_exit_one(self) -> None:
        case = build_examples()[0]
        malformed = ObservationResult("malformed", None, Lam("x", Var("x")), 2, 10000,
                                      "test malformed marker")
        with (
            temporary_directory() as temporary,
            patch.object(demo, "build_examples", return_value=(case,)),
            patch.object(demo, "observe", return_value=malformed),
            redirect_stdout(StringIO()) as output,
        ):
            self.assertEqual(demo.main(["--output-dir", temporary]), 1)
        self.assertIn("Observation: malformed", output.getvalue())
        self.assertIn("Observation diagnostic: test malformed marker", output.getvalue())
        self.assertIn("Decoded answer: unavailable", output.getvalue())
        self.assertIn("Check: FAIL", output.getvalue())

    def test_nested_pairs_can_also_be_reported_with_typed_answers(self) -> None:
        case = DemoCase("PAIR", "nested pair", ast.D0Epair(
            ast.D0Epair(ast.D0Eint(2), ast.D0Ebtf(True)), ast.D0Eint(3)),
            ("pair", ("pair", "natural", "boolean"), "natural"), ((2, True), 3))
        result = demo.run_example(case, execution_budget=100, observation_budget=100)
        self.assertTrue(result.passed)
        self.assertFalse(replace(result, source_answer=((2, 1), 3)).passed)
        self.assertEqual(demo._display(result.observation.value), "((2, true), 3)")


if __name__ == "__main__":
    unittest.main()
