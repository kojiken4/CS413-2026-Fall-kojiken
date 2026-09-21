# Assignment 02

## Interpreter changes

`lambda0.py` adds pairs and both projections to size counting, free-variable
analysis, substitution, and evaluation. Constructors each add one AST node;
free-variable analysis visits all children. Substitution preserves constructors
and existing lambda/recursive-function bindings, assuming closed replacements.
Pairs evaluate left to right, including an unselected component. Projections
first evaluate their operand and raise `TypeError` for non-pairs.

Function bodies and selected conditional branches now continue through an
evaluator loop, avoiding Python stack growth from tail calls. Argument order
and call-by-value behavior are preserved. No new primitive operators were needed;
absolute value and short-circuit conjunction use existing conditionals.

## ATS2 translation

`queens.dats` is an unchanged copy from `assigns/01/MySolution/queens.dats`,
credited to Hongwei Xi (2011; ATS2 port March 24, 2013), with its license retained.
`queens_lambda0.py` constructs a closed LAMBDA0 term and evaluates it with
`t0erm_cbv_evaluate0`. Python builds ASTs and decodes/displays results; the
interpreter performs the search, conflict checks, and list reversal.

| ATS2 source | LAMBDA0 mapping |
| --- | --- |
| `board_get`, `board_set` | `T0Mlam` functions using conditionals and projections; invalid indices return zero or the unchanged board. |
| `safety_test1` | Lambda checks unequal columns and unequal absolute row/column distances. |
| `safety_test2` | `T0Mfix` recursively checks earlier rows, stopping at a conflict. |
| `search` | `T0Mfix` preserves candidate order and backtracking; completed boards are accumulated instead of printed immediately. |
| `main0`, printing helpers | Build/apply the search term with `T0Mapp`; Python displays the returned values in the original format. |

Representations (`pair` abbreviates `T0Mpair`; literals are AST nodes):

- **Board:** eight zero-based columns, one per row, stored as
  `pair(c0, pair(c1, ... pair(c6, c7)))`.
- **Arguments:** multiple arguments are bundled the same way into one tuple.
- **Lists:** empty is `pair(false, 0)`; a node is `pair(true, pair(board, tail))`.
- **Search state:** `(board, row, column, count, reversed_solutions)` as a nested
  tuple. The initial board and counters are zero; the list is empty.
- **Result:** `pair(count, solutions)`. An interpreted tail-recursive reversal
  restores discovery order. The initial diagonal demonstration board is printed
  separately and is not counted as a solution.

## Run and verify

Use Python 3.12+ (verified with 3.14.7). From `assigns/02/MySolution`:

```powershell
python -B queens_lambda0.py
python -B -m unittest discover -s TEST -p "test*.py" -v
python -B TEST/compare_queens.py
```

The comparison additionally requires Windows with Ubuntu WSL and `patscc`.
It compiles and runs ATS2, runs the Python driver, checks exit codes, compares
complete stdout allowing only newline differences, and validates the boards.
Build artifacts and fresh outputs stay in ignored `.ats-build/`. Ordinary tests
use `reference/queens-ats-output.txt` and need no ATS2 compiler. All tests import
the submission's interpreter; the supplied regression tests remain unchanged.

**Results:** all 93 tests passed, including 92 distinct valid boards in exactly
the saved ATS2 order. Tests cover all four pair operations, binding boundaries,
evaluation order/errors, board operations, conflict checks, list handling, and
tail calls beyond Python's recursion limit. Fresh end-to-end comparison also
passed: both programs exited successfully and complete stdout matched after
newline normalization, including all 92 valid boards in order. The saved
reference matched the fresh ATS2 output. LAMBDA0 took 270.678 seconds. The final
audit reran the other 90 tests and confirmed the starter remained unchanged.

## Limitations and AI review

The translation stays at eight rows, matching this source, meaning that smaller boards are
not supported. The direct substitution-based search takes several minutes
(about four minutes for the full test suite here). Deep non-tail recursion and
recursive AST traversal can still reach Python's recursion limit.

AI assistance generated implementation, tests, and documentation incrementally.
Review covered variable scope, constructor-preserving substitution, eager pair
evaluation, ATS2 control-flow mapping, and the separation of AST construction
from interpreted execution. Tests were added before implementing each feature:
failures were checked, then existing and new tests were run. Source-copy hashes,
closed terms, and independent board-validity checks provided additional evidence.
These checks were executed by my AI, but I also manually audited the high-level changes made, as well as the overall behavior of the code that it wrote.
