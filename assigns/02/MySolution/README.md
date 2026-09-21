# Assignment 02

## Goal

Extend the LAMBDA0 interpreter with pairs and projections, then translate an
ATS2 eight-queens solver into a LAMBDA0 term executed by the interpreter.

## Current status: pair analysis, substitution, and evaluation

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
