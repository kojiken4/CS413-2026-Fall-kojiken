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

## Step 4 checks

`tests/test_model.py` tests the model directly without browser or server requests.
An isolated Python process imports the model and applies source while verifying
that FastAPI, the backend, constructor reader, and interpreter are not imported.

Cases cover initial manual entry, blank manual drafts over existing source,
Apply/Discard, uploads/canned replacements, identical-source reloads, immutable
snapshots, source names, and result invalidation on new revisions. Empty,
oversized, nontext, and invalid Unicode rejection preserves applied state;
rejected text remains correctable. Limits count UTF-8 bytes. Malformed constructor
syntax is accepted as source and left for the tools to diagnose.

All source operations require applied source; dirty/busy conflicts are rejected.
Execute remains unavailable, and artifacts remain absent. Completion validates
request ownership, operation, and revision; backend failure results preserve
source and restore availability. Wrong/stale completions cannot change state.
Cleanup is idempotent, and late completion/cleanup cannot affect newer requests.
A concurrent-start test verifies that only one request becomes active.

Observed on Python 3.13.14: **276 passed**, exit 0, with the existing dependency
warning. Oversized boundary-test identifiers were shortened after test setup
errors; the complete suite then passed. Supplied language semantics and the
browser/controller code were not changed. Upload-byte decoding, controller
orchestration, timeout, and browser smoke tests remain pending.

## Step 5 checks

`tests/test_bounded_backend.py` verifies the real subprocess path for Lint and
Interpret, recursive samples, runtime and input diagnostics, Unicode transport,
caller-directory independence, and the five-second default. Shorter timeouts are
injected for the recovery test; normal tests use the default.

A real Fibonacci(40) computation exceeds a one-second test timeout. The child is
stopped and reaped, source/revision are preserved, the model leaves busy state,
and Lint on unchanged source plus interpretation of corrected source succeed.
An async test waits using `asyncio.to_thread` and verifies that the event loop
continues running while the model blocks conflicting edits.

A genuinely nonterminating recursive LAMBDA expression returns a `RecursionError`
runtime diagnostic before the default deadline. This is separate from the real
slow-program timeout test; timeout is not simulated by that recursion case.

Worker crashes, process-creation failure, malformed responses, and a pipe failure
while a child is alive are injected to verify backend failure handling. Every
tracked child is reaped and every pipe is closed. Result validation checks identity,
revision, outcome and data types; Lint results retain `frozenset` semantics.
Type-check/Compile/Execute never launch workers.

Observed on Python 3.13.14: **319 passed in 2.90 seconds**, exit 0, with the existing
dependency warning. Controller/browser busy status, timeout recovery UI, and
real HTTP responsiveness remain pending until their integration steps.

## Step 6 checks

`tests/test_controller.py` exercises HTTP source workflows, strict request fields,
upload decoding/size boundaries and closure, correctable rejected edits, source
names/revisions, Apply/Discard, and dirty/busy prerequisites. Uploaded file edits
leave the original local file unchanged. A suspended upload rechecks replacement
permission after reading, preserving a draft edited while the read was pending.

An injected backend records dispatch without changing the view; independent app
instances have independent models. Malformed/stale backend results, unexpected
exceptions, and unsupported artifacts become failure results, preserving source
and allowing retry. Literal HTML-like output and line breaks survive JSON transport
with operation/revision/outcome metadata; this does not verify browser rendering.

Real bounded tools are tested through HTTP for factorial/Fibonacci, undeclared
variables, invalid constructors, runtime errors, placeholders, and timeout/retry.
Async request tests verify responsive state reads, conflict rejection, and HTTP
cancellation without prematurely releasing busy state. Work is recorded and
cleaned up even when its requesting HTTP task is cancelled.

Observed on Python 3.13.14: **364 passed in 5.17 seconds**, exit 0, with the existing
dependency warning. The resumed run fixed the invalid-Unicode test fixture:
HTTPX could not encode its lone surrogate before sending the request. Escaped
JSON now reaches the route and verifies rejected draft preservation correctly.

A temporary real Uvicorn server bound to `127.0.0.1` with one worker verified
manual entry/Apply, multipart upload, both canned samples, Lint/Interpret,
Type-check/Compile placeholders, and unavailable Execute. During Fibonacci(40),
a busy-state GET completed in **0.016 seconds** and Discard returned 409. The
default five-second timeout returned `backend_failure`, preserved source, restored
idle state, and allowed a subsequent interpretation returning `D0Vint(arg1=42)`.
Verification exited 0 and stopped that exact server process. This is HTTP evidence,
not a visual browser smoke test.

## Step 7 browser checks

Default tests: **364 passed, 7 skipped in 4.98 seconds**, exit 0. The seven
browser tests are opt-in; see README commands. Separately, all **7 browser tests
passed in 145.27 seconds**, exit 0, using Playwright 1.55.0 and installed Edge
154.0.4258.53 on Windows/Python 3.13.14. Every test starts and stops an independent
real loopback Uvicorn server and checks for uncaught browser script errors.
Dependency consistency and JavaScript syntax checks also passed. The existing
Starlette/HTTPX warning remains in the default suite.

| Browser steps | Expected | Observed |
| --- | --- | --- |
| Select Manual input; activate Load with Enter | Blank editor receives keyboard focus; actions need applied source | Passed; initial action buttons disabled |
| Type arithmetic, Apply, Interpret; edit and Discard; edit and Apply | Result 42; dirty guards; Discard preserves revision/results; Apply clears results and increments revision | Passed |
| Select Factorial and Fibonacci; run Lint/Interpret | Closed examples evaluate to 120 and 8 | Passed with real bounded tools |
| Enter open expression; Lint; close it and Lint again | Undeclared x error, then success | Passed |
| Enter division by zero; Lint then Interpret; enter malformed constructor | Lint succeeds, runtime failure differs from input error | Passed |
| Activate Type-check/Compile and inspect Execute | Explicit not-implemented outcomes; Execute disabled with generated-code explanation | Passed; correct button order |
| Choose a local file; reject invalid UTF-8/oversized files; reject empty/oversized edits; correct empty uploaded text | Applied source/revision/results preserved; rejected text remains correctable | Passed; source names and revisions displayed |
| Enter HTML-like source; display HTML-like multiline output | Literal characters, preserved newline, no injected elements/scripts | Passed; source and Lint are real, only multiline output response is injected for the rendering check |
| Delay the first draft response while typing newer text, then Apply | Latest text wins; Apply waits for draft synchronization | Passed; interpreted latest expression as 42 |
| Abort a draft request; restore connection and retry Apply | Local edits preserved and tools blocked until synchronization succeeds | Passed |
| Run Fibonacci(40), inspect busy controls/state, then correct source and retry | Page remains responsive; conflicting controls locked; timeout preserves source and restores controls | Passed; real five-second timeout followed by result 42 |

Desktop (1100-pixel viewport) and narrow-screen (390-pixel viewport) screenshots
were rendered and visually inspected after real factorial interpretation. Labels,
controls, source, explanations, and results were readable; controls wrap on the
narrow screen without page overflow. Temporary screenshots are in ignored
`.venv/` and are not submission artifacts. Screen-reader behavior was not
manually audited; native labels, focus behavior, textual status/live alerts, and
keyboard activation were checked.

The initial browser run found three test-fixture issues: an incorrect empty-source
message expectation, a mishandled delayed route, and an assertion deadline equal
to the worker timeout. These were corrected before the passing run; no backend
or supplied interpreter changes were needed.

## Requirement traceability

| Requirement | Required checks | Current status |
| --- | --- | --- |
| F1 | Upload, manual entry, editable factorial/Fibonacci, source name/revision | Model/HTTP tests and browser source-menu/name/revision checks passed |
| F2 | Initial typing, editing, Apply/Discard, dirty-state guards | Model/HTTP tests and browser editing/guards passed; original-file preservation tested through HTTP |
| F3 | Empty/UTF-8/size rejection, preservation of state and edits | Reader/model/HTTP tests and browser rejection/correction checks passed |
| F4 | Button order, applied-source prerequisite, disabled Execute | HTTP guards and browser button order/disabled states passed |
| F5 | Real Lint, lexical scope, deterministic undeclared names | Backend/HTTP tests and browser open/closed reporting passed |
| F6 | Real evaluation, arithmetic/examples/base cases, input/runtime errors | Backend/HTTP tests and browser arithmetic/examples/error display passed |
| F7 | Explicit placeholders and disabled Execute explanation | HTTP tests and browser placeholder messages/Execute explanation passed |
| F8 | Revision increment and results/artifacts invalidation | Model/HTTP tests and browser Apply/Discard/result clearing passed; artifacts always absent |
| F9 | Operation/revision/outcome, line breaks, literal HTML-like text | JSON tests and browser metadata/literal multiline rendering passed |
| F10 | Busy state, conflicting work, bounded execution, failure/retry | Model/HTTP tests, real server checks, and browser timeout/network-error/retry checks passed |

Clean-checkout setup verification remains for Step 9. Browser checks above use
the current working environment, not a clean checkout.
