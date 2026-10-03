# Verification

## Recorded results

Verification was performed on Windows with Python 3.13.14 and the pinned direct
dependencies in `requirements-dev.txt`. These are recorded observations from
October 2, 2026; commands to reproduce them are in [README.md](README.md).

| Check | Recorded result |
| --- | --- |
| Default automated suite | **364 passed, 7 opt-in browser tests skipped**, exit 0 |
| Browser suite in a fresh checkout | **All 7 passed** on Chromium 140.0.7339.16, exit 0 |
| Additional browser run | All 7 passed on installed Edge 154.0.4258.53 |
| Dependency consistency and JavaScript syntax | Passed |
| Clean-checkout setup and server requests | Passed on Windows/Python 3.13.14 |

Pytest emits a Starlette 1.7.0 deprecation warning recommending `httpx2` for its
test client. Checks pass with the pinned HTTPX 0.28.1. macOS instructions were
reviewed against Python and Playwright documentation but not executed on a Mac.
Manual screen-reader behavior and other platforms are unverified.

## Automated coverage

| Test module | Verified behavior |
| --- | --- |
| [test_foundation.py](tests/test_foundation.py) | Landing HTML, unknown-route handling, supplied interpreter import/arithmetic |
| [test_constructor_reader.py](tests/test_constructor_reader.py) | All 13 constructors; positional/named/mixed arguments; comments/multiline input; scalar types; rejected Python syntax; transport and nesting boundaries |
| [test_backend.py](tests/test_backend.py) | Real lexical scope and evaluation; deterministic free-variable diagnostics; error classification; placeholders and unavailable Execute |
| [test_model.py](tests/test_model.py) | Framework-independent state rules, revisions, drafts, Apply/Discard, busy guards, request ownership and recovery |
| [test_bounded_backend.py](tests/test_bounded_backend.py) | Real worker execution, timeout/cleanup, Unicode transport, malformed responses and retry |
| [test_controller.py](tests/test_controller.py) | HTTP workflows, injected backend dispatch, upload validation/races, state preservation, cancellation and recovery |
| [test_browser.py](tests/test_browser.py) | Opt-in real-browser interaction and rendering checks described below |

Constructor-reader boundaries include exactly 64 KiB, oversized and multibyte
UTF-8, whitespace-only/nontext/invalid Unicode input, and excessive nesting.
Reading a closed division-by-zero constructor is checked with Python execution
and LAMBDA evaluation blocked. A rejected file-write expression creates no file.

Free-variable tests cover every constructor, duplicate occurrences, shadowing,
nested bindings, recursive function/parameter scope, nonrecursive let initializer
scope, unused bindings, and both conditional branches. Lint returns a
`frozenset`, sorts undeclared names, and does not evaluate source.
Real interpretation covers arithmetic, booleans, conditionals, let/lambda
application, pairs/projections, and closure values. Factorial cases 0, 1, and 5
produce 1, 1, and 120; Fibonacci cases 0, 1, and 6 produce 0, 1, and 8.
Malformed input, runtime failures, and exact `D0V000()` sentinels directly or
inside pairs are distinguished. Interpret uses an empty environment independently
of Lint. Type-check/Compile neither parse source nor produce artifacts; Execute
does not compile or interpret source.

Model tests run without browser/server requests. An isolated import check
verifies that using the model does not import FastAPI, the backend, reader, or
interpreter. Tests cover immutable snapshots, rejected correctable drafts,
source names, identical-source reloads, revision/result invalidation, dirty/busy
guards, atomic concurrent starts, and idempotent cleanup. Wrong/stale completion
or cleanup cannot affect newer work.

Bounded tests use real processes. Fibonacci(40) exceeds a one-second test timeout;
the child is reaped, pipes close, source is preserved, and retry succeeds.
A nonterminating recursive expression instead reaches Python's recursion limit
and returns a runtime diagnostic. Injected crash/creation/pipe/protocol failures
verify adapter recovery. Async waiting leaves the event loop responsive.

Controller tests substitute a backend without changing view code, while separate
cases exercise real tools through HTTP. Upload checks cover strict UTF-8,
size boundaries, closure, original-file preservation, and rechecking permission
after a suspended read. HTTP cancellation retains busy state until actual
completion; malformed backend results become failures and allow retry.

Mocks are limited to dispatch, injected failures/delays, and output rendering.
They do not replace the required real Lint and Interpret checks.

## Browser observations

Each opt-in test starts and stops an independent loopback Uvicorn server and
checks for uncaught browser script errors. All seven passed with Playwright
1.55.0 on Edge 154.0.4258.53 (145.27 seconds) and, independently in a fresh
environment, Chromium 140.0.7339.16 (20.70 seconds).

| Browser procedure | Expected | Observed |
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
controls, source, explanations, and results were readable. Controls wrap without
page overflow on the narrow screen. Temporary screenshots are in ignored
`.venv/`, excluded from submission. Native labels, focus, textual status/live
alerts, and keyboard activation were checked; manual screen-reader use was not.

The README demonstrations were also checked through controller requests with real
bounded tools. The division-by-zero diagnostic is
`ZeroDivisionError: integer division or modulo by zero`.

## Clean-checkout verification

On **October 2, 2026**, a separate local clone of commit
`669b4d4c422b54b5af86036412f869df62e4c26c` was created with
`git clone --no-hardlinks --single-branch`. Its tracked working tree remained
clean. The documented `py -3.13 -m venv .venv` created a fresh environment,
independent of the development environment. The clone and generated browser
cache/dependencies are inside the original solution's ignored `.venv/`.

| Check in isolated checkout | Observed |
| --- | --- |
| Install `requirements-dev.txt` | Passed, exit 0; all six direct pinned versions matched |
| `python -m pytest -q` | **364 passed, 7 skipped in 5.36 seconds**, exit 0 |
| `python -m pip check` | No broken requirements, exit 0 |
| `python -m playwright install chromium` | Fresh Chromium 140.0.7339.16 installed, exit 0 |
| Opt-in `tests/test_browser.py` | **All 7 passed in 20.70 seconds**, exit 0 |
| Loopback startup, HTML/static assets, manual Apply/Interpret | Passed; interpretation returned `D0Vint(arg1=42)` |
| Supplied interpreter comparison | Byte-for-byte match |
| Documentation links/fences/reflection | Passed; reflection is 249 words |
| Tracked submission files | No virtual environments, caches, or bytecode tracked |

Interpreter SHA256:
`4024AB0AB1F32D2F38B4CB30A86EC9633C1280A6385A15971B929C7D7D05FE5F`.

Port 8000 was occupied by an existing Python listener, which was left running.
Startup was verified on port 8001 with the documented command's port changed.
The README explains choosing an unused port. Verification servers and browsers
were stopped. These results concern the committed application snapshot;
subsequent documentation edits do not represent additional platform testing.

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
