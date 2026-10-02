# Verification

## Step 1 checks

Automated tests in `tests/test_foundation.py` cover the landing page response,
unknown-route handling, and import/use of the supplied interpreter.
The interpreter copy is also compared byte-for-byte with the provided file.
Observed results on Python 3.13.14 (Windows):

| Check | Expected | Observed |
| --- | --- | --- |
| Install from `requirements-dev.txt` | Pinned direct dependencies install | Passed, exit 0 |
| `python -m pip check` | No broken dependencies | Passed, exit 0 |
| `python -m pytest -q` | Foundation tests pass | 3 passed in 0.37 seconds, exit 0 |
| Interpreter SHA256 comparison | Copy matches supplied bytes | Passed; both hashes are `4024AB0AB1F32D2F38B4CB30A86EC9633C1280A6385A15971B929C7D7D05FE5F` |
| Start documented Uvicorn command and request `/` over HTTP | 200 with landing-page HTML | Passed at `http://127.0.0.1:8000/`; verification process stopped afterward |
| Git ignore check for `.venv/pyvenv.cfg` | Environment excluded | Passed |

Pytest emitted one dependency deprecation warning: Starlette 1.7.0 recommends
`httpx2` instead of HTTPX for its test client. Tests still pass with the pinned
HTTPX 0.28.1; this warning does not indicate an application failure.
The HTTP check is a real server request, not a visual browser smoke test.

## Step 2 checks

`tests/test_constructor_reader.py` tests all 13 expression constructors with
positional and named arguments, missing/extra arguments and wrong field types,
comments, multiline input, mixed arguments, signed integers, Unicode and escaped
strings, duplicate/unknown fields, and rejected Python execution syntax.

Boundary cases include exactly 64 KiB, exceeding the limit, multibyte UTF-8,
whitespace-only input, nontext input, invalid Unicode, and excessive nesting.
A test blocks Python `eval`/`exec` and LAMBDA evaluation while reading a closed
division-by-zero constructor. A rejected file-write expression creates no file.

Observed: full suite **129 passed**, exit 0, on Python 3.13.14. The existing
Starlette/HTTPX deprecation warning remains. The first run caught an incorrectly
escaped newline in a test fixture, which was corrected. One invocation from the
repository root failed imports; the documented invocation from `MySolution`
passed. Constructor parsing and transport checks are not evidence of completed
Lint, Interpret, editing, or browser workflows.

## Step 3 checks

`tests/test_backend.py` calls the real supplied `d0exp_fvset` and evaluator for
normal operation. Its free-variable cases cover all 13 constructors, duplicate
occurrences, lexical shadowing/nested bindings, recursive name/parameter scope,
nonrecursive let initializer scope, unused bindings, and both conditional branches.
Lint returns a `frozenset`, sorts diagnostics, and does not evaluate closed
source that would divide by zero.

Real evaluation cases cover arithmetic, booleans, conditionals, let/lambda
application, pairs/projections, and successful lambda/fix closure values.
Factorial tests include 0, 1, and 5 (results 1, 1, 120); Fibonacci tests include
0, 1, and 6 (results 0, 1, 8), using the actual sample files.

Error checks distinguish malformed input, runtime type/arithmetic errors, exact
sentinels directly or nested in pairs, unexpected tool failures, and invalid tool
returns. Interpretation is verified independent of Lint with an empty environment.
Mocks inject unexpected failures/recursion errors and verify adapter retry; these
are not replacements for real Lint or Interpret tests. Placeholders neither parse
source nor produce artifacts; Execute calls neither compilation nor interpretation.

Observed on Python 3.13.14: **199 passed in 0.39 seconds**, exit 0. The existing
Starlette/HTTPX warning remains. An initial run caught misuse of a Python type
alias in a runtime value check; the adapter now checks the concrete supplied
`D0V000` class. The supplied interpreter still matches its original SHA256.
No timeout, busy-state, controller dispatch, or browser-action checks are claimed.

## Requirement traceability

| Requirement | Required checks | Current status |
| --- | --- | --- |
| F1 | Upload, manual entry, editable factorial/Fibonacci, source name/revision | Pending |
| F2 | Initial typing, editing, Apply/Discard, dirty-state guards | Pending |
| F3 | Empty/UTF-8/size rejection, preservation of state and edits | Reader text/size checks tested; upload/state checks pending |
| F4 | Button order, applied-source prerequisite, disabled Execute | Pending |
| F5 | Real Lint, lexical scope, deterministic undeclared names | Backend tested; browser reporting pending |
| F6 | Real evaluation, arithmetic/examples/base cases, input/runtime errors | Backend tested; browser display pending |
| F7 | Explicit placeholders and disabled Execute explanation | Backend responses tested; controls pending |
| F8 | Revision increment and results/artifacts invalidation | Pending |
| F9 | Operation/revision/outcome, line breaks, literal HTML-like text | Pending |
| F10 | Busy state, conflicting work, bounded execution, failure/retry | Adapter failure/retry tested; busy/timeout/HTTP checks pending |

The full browser smoke test and clean-checkout setup verification remain pending.
A landing route response is not evidence that those checks have passed.
