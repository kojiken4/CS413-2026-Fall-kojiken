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

## Requirement traceability

| Requirement | Required checks | Current status |
| --- | --- | --- |
| F1 | Upload, manual entry, editable factorial/Fibonacci, source name/revision | Pending |
| F2 | Initial typing, editing, Apply/Discard, dirty-state guards | Pending |
| F3 | Empty/UTF-8/size rejection, preservation of state and edits | Pending |
| F4 | Button order, applied-source prerequisite, disabled Execute | Pending |
| F5 | Real Lint, lexical scope, deterministic undeclared names | Pending |
| F6 | Real evaluation, arithmetic/examples/base cases, input/runtime errors | Pending |
| F7 | Explicit placeholders and disabled Execute explanation | Pending |
| F8 | Revision increment and results/artifacts invalidation | Pending |
| F9 | Operation/revision/outcome, line breaks, literal HTML-like text | Pending |
| F10 | Busy state, conflicting work, bounded execution, failure/retry | Pending |

The full browser smoke test and clean-checkout setup verification remain pending.
A landing route response is not evidence that those checks have passed.
