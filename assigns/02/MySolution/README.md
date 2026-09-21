# Assignment 02

## Goal

Extend the LAMBDA0 interpreter with pairs and projections, then translate an
ATS2 eight-queens solver into a LAMBDA0 term executed by the interpreter.

## Current status: pair support and translated board operations complete

`lambda0.py` extends the starter's `t0erm_size` and `t0erm_fvset` with
pair and projection cases. A pair counts as one node plus both children's
sizes; a projection counts as one node plus its operand's size. Free-variable
analysis unions both components' variables or visits a projection's entire
operand. Neither constructor binds variables or evaluates expressions.
`TEST/test01_lambda0.py` is an unchanged copy of the supplied regression tests.
`TEST/test02_lambda0.py` adds nine tests for these analysis operations,
including nesting, duplicate variables, lambda scope, and recursive binders.
`t0erm_subst0` now substitutes recursively into both pair components and each
projection's operand, preserving the constructors without evaluating them.
Existing lambda and recursive-function binders still protect their bound names.
The replacement term must still be closed (have no free variables); this is
the starter's assumption, not a new runtime check.
Nine additional tests cover substitution, nesting, scope boundaries, closed
pair/function replacements, and preservation of the original input tree.
`t0erm_cbv_evaluate0` now evaluates pairs left to right and returns their
evaluated components in a pair. Projections evaluate their operand before
selecting a component and raise TypeError if the resulting value is not a pair.
Both pair components are evaluated even if a projection selects only one.
Functions inside pairs remain values; their bodies execute only on application.
Twelve evaluation tests cover these rules, nested/mixed values, function calls,
recursive-function values, and error propagation. The queens translation remains
pending.

Step 5 adds the unchanged ATS2 source, its captured output, and four reference
tests in `TEST/test03_queens.py`. These tests check the ATS2 reference only;
they do not yet compare it with a translated LAMBDA0 solver.

Step 6 adds `queens_lambda0.py` with closed `BOARD_GET` and `BOARD_SET` function
ASTs, plus nine tests in `TEST/test03_queens.py` for board operations and their
construction helpers. Conflict checking, search, and the full driver remain
pending; running `queens_lambda0.py` by itself does not yet run a solver.

The test file adds its parent directory (`MySolution`) to Python's import path,
so it tests this directory's interpreter rather than the assignment starter.

## Run tests

Requires Python 3.12 or later. From `assigns/02/MySolution`, run:

```powershell
python -B -m unittest discover -s TEST -p "test*.py" -v
```

`-B` prevents Python from writing bytecode cache files. The tests cover existing
evaluation behavior, including arithmetic, functions, recursion, conditionals,
evaluation order, error cases, and Church numerals (numbers encoded as functions).
They provide a baseline for detecting regressions as the interpreter is extended.

## ATS2 source and reproducible reference

`queens.dats` is copied byte-for-byte from `assigns/01/MySolution/queens.dats`.
Its header credits Hongwei Xi, January 2011, with the ATS2 port dated March 24,
2013. The copyright and permission notice are preserved. Both local copies
had this SHA-256 hash when the reference was captured:

```text
CD533C47C86593861AFECEC2A02732A06B4E14FF8667052B4358671B38C9605A
```

The source fixes N at eight. It prints an initial demonstration board with
columns `(0, 1, 2, 3, 4, 5, 6, 7)`, then enumerates solutions and asserts that
the count is 92. The demonstration board has diagonal conflicts and is NOT a
solution. The test parser excludes it and retains solution discovery order.

The unchanged copy was compiled and run using Ubuntu WSL's `patscc`, with exit
code zero. `reference/queens-ats-output.txt` stores its actual stdout, including
the demonstration board. Tests verified 92 distinct, valid solution boards:

- First: `(0, 4, 7, 5, 2, 6, 1, 3)`.
- Last: `(7, 3, 0, 2, 5, 1, 6, 4)`.

To regenerate the reference from PowerShell in `assigns/02/MySolution`:

```powershell
wsl -d Ubuntu -- bash -c 'set -e; mkdir -p .ats-build reference; cd .ats-build; patscc -o queens ../queens.dats; ./queens > ../reference/queens-ats-output.txt'
if ($LASTEXITCODE -ne 0) { throw "ATS2 reference generation failed" }
python -B -m unittest discover -s TEST -p "test03_queens.py" -v
```

Compilation places the executable and generated C in `.ats-build/`, which is
ignored by Git. Running the tests alone needs Python but does not require WSL
or the ATS2 compiler. A fresh original-versus-translation comparison is still
required once the translation exists.

## LAMBDA0 representations

Boards and bundled arguments below are implemented in step 6. Solution lists,
search state, and the final result remain planned for later steps.

The notation `pair(a, b)`, `first(p)`, and `second(p)` below abbreviates
`T0Mpair`, `T0Mpfst`, and `T0Mpsnd` expressions. Integers and booleans in these
examples mean `T0Mint` and `T0Mbtf` nodes, not raw Python values in the AST.

### 1. Boards: row positions stored in nested pairs

Store eight columns in a fixed, right-nested tuple:

```text
board = pair(c0, pair(c1, pair(c2, pair(c3, pair(c4, pair(c5, pair(c6, c7)))))))
```

The row is the position in the tuple; the integer at that position is the
queen's column. All indices are zero-based. For example, the first reference
solution has `c0 = 0`, `c1 = 4`, and `c2 = 7`, so the queen in row 2 is in
column 7. `first(second(second(board)))` retrieves that 7. The last column
is reached by seven `second` operations, with no final `first`.

There is no end marker because a board always has eight entries. Partial
boards also have eight entries, but safety checks inspect only earlier rows.
The initial search board contains eight zeros, matching the ATS2 source.

### 2. Multiple arguments: one bundled tuple

LAMBDA0 functions have one parameter. Bundle multiple arguments into nested
pairs, with the final field stored directly, just as for boards:

```text
board_get(board, 2)    -> apply(board_get_term, pair(board, 2))
board_set(board, 2, 5) -> apply(board_set_term, pair(board, pair(2, 5)))
```

A two-argument function extracts its first argument with `first(args)` and
its second with `second(args)`. A three-argument function extracts its last
argument with `second(second(args))`. Python helpers may build these ASTs;
the interpreter must perform the actual lookup or update.

### 3. Solution lists: tagged empty/nonempty values

Boards have fixed size, but a solution list has variable length. Use a boolean
tag to distinguish an empty list from a node holding one board and the rest:

```text
empty             = pair(false, 0)
cons(board, rest) = pair(true, pair(board, rest))
two boards        = cons(boardA, cons(boardB, empty))
```

`first(list)` is the boolean indicating whether a node exists. For a nonempty
list, `first(second(list))` is its board and `second(second(list))` is its tail.
The zero in `empty` is unused padding. Use `T0Mif0` to check the tag before
extracting the head or tail; projecting through the empty payload would fail.

The interpreted search prepends discovered boards to an accumulator. After
finding boardA and then boardB, that accumulator is `[boardB, boardA]`. A
LAMBDA0 list-reversal function will restore `[boardA, boardB]` before returning
the result, preserving ATS2 discovery order.

### 4. Search state and final result

Bundle the search state as:

```text
pair(board, pair(row, pair(column, pair(count, reversed_solutions))))
```

This preserves the source's four arguments and adds an explicit solution list
in place of printing during the search. Initially row, column, and count are
zero and the list is empty. The final result will be:

```text
pair(92, solutions_in_discovery_order)
```

`first(result)` retrieves the count; `second(result)` retrieves the solution
list. Python may decode, check, and print these returned values. It must not
perform the queen search or supply precomputed reference boards to the solver.

## Function mapping (board_get and board_set implemented; others planned)

| ATS2 function | LAMBDA0 translation and example |
| --- | --- |
| `board_get(bd, i)` | Lambda with bundled arguments; conditionals and projections select an entry. For the first reference board, index 2 returns 7. An index outside 0 through 7 returns 0, matching ATS2. |
| `board_set(bd, i, j)` | Lambda builds a new nested tuple. Setting index 2 to 5 changes only that entry. An out-of-range index returns the original board. |
| `safety_test1(i0, j0, i, j)` | Lambda checks different columns and different diagonals. `(1, 2)` versus `(0, 0)` is safe; `(1, 1)` versus `(0, 0)` is diagonal conflict; `(1, 0)` versus `(0, 0)` is column conflict. Row uniqueness is enforced by the search. |
| `safety_test2(i0, j0, bd, i)` | Recursive `T0Mfix` checks previous rows down to zero. Candidate `(2, 4)` is safe relative to rows 0 and 1 at columns 0 and 2. With `i = -1`, no previous rows remain, so return true. |
| `search(bd, i, j, nsol)` | Recursive `T0Mfix` uses the five-field state above. A safe placement in row 0 advances to row 1, column 0; a conflict tries the next column; exhausting columns backtracks; filling row 7 records a board and continues. Exhausting row 0 ends the search. |
| `print_dots`, `print_row`, `print_board` | Python display helpers reproduce presentation after decoding the interpreted result. Column 2 displays as `. . Q . . . . .`. The initial demonstration board is presentation, not a solution. |
| `main0` | Construct a closed search term, evaluate it, decode the count and ordered boards, and verify the count is 92. For example, require `t0erm_fvset(complete_term) == frozenset()` before evaluation. |

Existing integer comparison primitives suffice. Express absolute value as a
conditional (`if d < 0 then -d else d`) and `andalso` as `if a then b else false`
to preserve short-circuit behavior. Function definitions will be explicitly
bound in the complete term; names such as `board_get_term` above are explanatory
placeholders, not unresolved free variables permitted in the final AST.

Call-by-value evaluates bundled arguments and pair fields eagerly, while an
`if` evaluates only its selected branch. The planned tail-call evaluator step
will address Python stack growth during the long sequence of search calls.
The translation stays at eight rows, as required by this particular source;
smaller-board generalization is outside this design.

## Using the translated board operations

`tuple_term(*fields)` builds a nested-pair AST with at least two fields.
`tuple_item(term, index, size)` builds projections for a fixed, valid field
position; its index is a Python construction-time constant. `make_board`
encodes exactly eight integer literals. It rejects incorrect lengths and
non-integers, but permits any integer column, matching the source's `int8`
data rather than enforcing queen safety at this stage.

In contrast, `BOARD_GET` and `BOARD_SET` are LAMBDA0 functions whose index is
supplied at runtime. They use eight conditional branches, in the same order
as ATS2. Python loops build those branches once; Python does not choose the
runtime branch or read/update a runtime board. Neither function has free
variables. No changes to the interpreter were needed for this step.

For example, run the following in Python from `MySolution`:

```python
from lambda0 import T0Mint, T0Mapp, t0erm_cbv_evaluate0
from queens_lambda0 import BOARD_GET, BOARD_SET, make_board, tuple_term

board = make_board((0, 4, 7, 5, 2, 6, 1, 3))
lookup = T0Mapp(BOARD_GET, tuple_term(board, T0Mint(2)))
assert t0erm_cbv_evaluate0(lookup) == T0Mint(7)

update = T0Mapp(BOARD_SET, tuple_term(board, T0Mint(2), T0Mint(5)))
changed = t0erm_cbv_evaluate0(update)
assert changed == make_board((0, 4, 5, 5, 2, 6, 1, 3))
assert board == make_board((0, 4, 7, 5, 2, 6, 1, 3))

outside = T0Mapp(BOARD_GET, tuple_term(board, T0Mint(8)))
assert t0erm_cbv_evaluate0(outside) == T0Mint(0)
unchanged = T0Mapp(BOARD_SET, tuple_term(board, T0Mint(-1), T0Mint(5)))
assert t0erm_cbv_evaluate0(unchanged) == board
```

The updated example has a column conflict, which is allowed: `board_set` only
replaces an entry. The next step implements the separate safety checks.

## Verification and AI assistance

Baseline verification passed all 27 supplied tests using Python 3.14.7.
The loaded module's resolved path was checked after test discovery and confirmed
to be `MySolution/lambda0.py`. File hashes confirmed that the interpreter and
copied test file match their respective starter files.

AI assistance was used to copy the supplied tests, draft this README, and run
the baseline checks. No interpreter logic was changed in this step. This records
the checks performed by the assistant; student review is a separate step.

For step 2, AI assistance added the analysis tests before changing the two
functions. The new tests initially raised TypeError on the unsupported
constructors. After adding the cases, all 36 tests passed (27 supplied tests
and nine new tests). Existing lambda and recursive-function binding logic was
preserved. The original starter outside MySolution was not edited.

For step 3, AI assistance added nine substitution tests and confirmed that
they failed on the missing pair/projection cases before implementing those
cases. All 45 tests then passed (27 supplied, nine analysis, nine substitution).
The change adds only constructor-preserving traversal to substitution; it does
not change binding rules or the evaluator. Student review remains separate.

For step 4, AI assistance added evaluation tests first and observed failures
for the unsupported pair/projection cases. After extending the evaluator,
all 57 tests passed (27 supplied, nine analysis, nine substitution, twelve
evaluation). Distinct errors in left and right components verify evaluation
order; division errors in unselected components verify strict pair evaluation.
Student review remains separate from these assistant-run checks.

For step 5, AI assistance copied the source unchanged, checked its hash,
compiled and executed it in WSL, captured stdout, and added reference checks.
All 61 tests passed: the previous 57 plus four reference tests. The reference
checks cover board validity, uniqueness, count, order endpoints, and malformed
output rejection. The complete output retains all 92 boards in order for the
future translation comparison. The representation and function mapping above
are design decisions, not claims that the solver translation is implemented.

For step 6, AI assistance wrote nine tests before adding the translation module;
the initial run failed because that module did not exist. After implementation,
all 70 tests passed. Checks cover every board index, unchanged entries and input
boards, negative/too-large indices, computed arguments, nested get/set calls,
closedness, and construction-helper boundaries. Board results are inspected
directly in tests rather than relying on board_get to validate board_set.
The README's usage assertions were also executed successfully. These checks
verify the board operations, not equivalence of the unfinished full solver.
