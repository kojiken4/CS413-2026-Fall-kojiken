# LAMBDA Web Front-End

Assignment 04: a local, single-user MVC application using the supplied,
unchanged LAMBDA interpreter. Python **3.12 or later** is required; implementation
and tests were verified with **Python 3.13.14 on Windows**.

Runtime dependencies: FastAPI 0.142.2, Uvicorn 0.54.0, python-multipart 0.0.32.
Test dependencies: pytest 9.1.1, HTTPX 0.28.1, Playwright 1.55.0.
Pinned declarations are in [requirements.txt](requirements.txt) and
[requirements-dev.txt](requirements-dev.txt).

## Setup and start

**Windows (PowerShell):** run from the repository root:

```powershell
Set-Location assigns/04/MySolution
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn lambda_web.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

**macOS (Terminal, zsh or bash):** with Python 3.13 installed and available as
`python3.13`, run from the repository root:

```sh
python3.13 --version
cd assigns/04/MySolution
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m uvicorn lambda_web.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

If using another supported Python version, replace `python3.13` with that
interpreter's command; verify it is Python 3.12 or later. macOS environments use
`bin/python` rather than Windows' `Scripts/python.exe`, as described in
[Python's virtual-environment documentation](https://docs.python.org/3.13/library/venv.html).
The macOS commands have been reviewed but not executed on a Mac.

Open [the application](http://127.0.0.1:8000/). Stop with Ctrl+C.
Keep the server on loopback with **one worker**. Activation is unnecessary.
If port 8000 is already in use, change `--port 8000` to an unused port such as
`--port 8001` and open `http://127.0.0.1:8001/` instead.
Virtual environments and caches are ignored by Git. For running the application
without test tools, install `requirements.txt` instead.

## Tests

From `MySolution`, **Windows (PowerShell):**

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
```

**macOS (Terminal):**

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m pip check
```

The default suite skips the seven opt-in browser tests. To run them on
**Windows (PowerShell):**

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
$env:LAMBDA_BROWSER_TESTS = "1"
.\.venv\Scripts\python.exe -m pytest tests/test_browser.py -q
Remove-Item Env:LAMBDA_BROWSER_TESTS
```

**macOS (Terminal):**

```sh
.venv/bin/python -m playwright install chromium
LAMBDA_BROWSER_TESTS=1 .venv/bin/python -m pytest tests/test_browser.py -q
```

The macOS environment-variable assignment applies only to that test command;
no cleanup command is needed. Chromium installation follows
[Playwright's browser setup instructions](https://playwright.dev/python/docs/browsers).

Alternatively, skip the Chromium download and set
`$env:LAMBDA_BROWSER_CHANNEL = "msedge"` before running browser
tests in PowerShell to use installed Edge. Remove that variable afterward with
`Remove-Item Env:LAMBDA_BROWSER_CHANNEL`. Each browser test starts
and stops its own loopback server. The macOS equivalent, if Edge is installed, is
`LAMBDA_BROWSER_TESTS=1 LAMBDA_BROWSER_CHANNEL=msedge .venv/bin/python -m pytest tests/test_browser.py -q`.

Clean-checkout verification on Windows/Python 3.13.14 passed: **364 default tests**
and **all seven browser tests** separately, using freshly installed Chromium
140.0.7339.16. Installation, dependency checks, loopback startup, and real requests
also passed. The verified checkout is commit `669b4d4`; final verification
details and F1–F10 mappings are in [TESTING.md](TESTING.md).

## Using the interface

Choose an item in **Load source**, then press **Load source**. Choose File opens
a local UTF-8 file chooser, Manual input opens a blank editor, and the canned
examples load editable expressions. Initial typing also works without an upload.
The page displays the applied source name and revision.

Typing updates a draft. **Apply changes** accepts it as a new revision and clears
results; **Discard changes** restores applied text without changing the revision.
Unapplied edits block tools and source replacement. Applied edits affect the
application's copy, never the original local file. Busy status locks conflicting
controls until work completes or fails.

Results show their action, source revision, outcome, and literal text with line
breaks preserved. Lint and Interpret can be invoked independently.

## Demonstration

1. Select **Factorial (canned)**, press **Load source**, then **Lint** and
   **Interpret**. Expect `success` and `D0Vint(arg1=120)` for factorial(5).
   Select **Fibonacci (canned)** and repeat; expect `D0Vint(arg1=8)` for
   Fibonacci(6). Accepted loads increment the revision and clear prior results.
2. Select **Manual input**, load it, enter `D0Evar("x")`, and **Apply changes**.
   **Lint** reports `language_error` with `Undeclared variables: 'x'`.
   Replace the text with `D0Eint(42)`, apply it, and lint again.
   Expect `success` with “No free variables were found.”
3. Replace the editor text with `D0Eop2("/", D0Eint(1), D0Eint(0))`
   and apply it. **Lint** succeeds because the expression is closed.
   **Interpret** reports `runtime_error` with a division-by-zero diagnostic.
   Passing Lint therefore does not guarantee successful evaluation.
4. With clean applied source, press **Type-check** and **Compile**. Both return
   `not_implemented`, with “Type checking is not yet implemented.” and
   “Compilation is not yet implemented.” **Execute** remains disabled: it is
   reserved for generated code, and Compile produces no artifact.

Sample files in [samples/](samples/) contain factorial, Fibonacci, an open
variable, division by zero, and invalid constructor input. These demonstrations
were exercised in the Step 7 browser tests.

## Constructor input

Input is **one Python constructor expression**, not a Python script. Constructor
names need no imports; comments and multiline nesting are supported:

```python
D0Eop2("+", D0Eint(20), D0Eint(22))
D0Eint(arg1=-42)
D0Epair(arg2=D0Ebtf(False), arg1=D0Eint(+1))
```

Supported constructors: `D0Eint`, `D0Ebtf`, `D0Evar`,
`D0Eop1`, `D0Eop2`, `D0Elam`, `D0Efix`,
`D0Eapp`, `D0Eif0`, `D0Elet`, `D0Epair`,
`D0Epfst`, and `D0Epsnd`. Arguments follow the supplied dataclass
fields; positional, named, and mixed arguments are accepted. Missing, extra,
unknown, duplicate, or incorrectly typed fields are rejected. Booleans and
integers are distinct; signed integer literals are accepted.

The restricted AST reader allows only these calls and their expected literals.
It rejects statements, imports, arbitrary calls, attributes, comprehensions,
formatted strings, and argument expansion. It never executes uploaded Python.
Malformed constructor syntax may be applied, then diagnosed by Lint/Interpret.

## Bounds and limitations

- Source must be nonempty UTF-8 text of at most **65,536 bytes (64 KiB)**,
  including whitespace/comments. Rejected edits stay correctable. Empty uploads
  retain a correctable draft; undecodable or oversized uploads preserve the
  existing draft and applied state. Multipart parsing may spool data before the
  application checks the size; it is not an HTTP request-body limit.
- Lint/Interpret use a fresh trusted worker with a **five-second timeout** covering
  startup, parsing, processing, and response transport after OS process creation.
  Process creation and cleanup may add overhead. Timed-out workers are killed
  and waited for; source is preserved and controls permit retry.
- Python parser nesting and evaluator recursion limits still apply. Runtime
  errors and exact `D0V000()` sentinels, including inside pairs, are reported
  as errors. Lint computes free variables without evaluating source.
- Type-check/Compile are placeholders. No generated artifact or generated-code
  executor is implemented. The intended future contract is in
  [ARCHITECTURE.md](ARCHITECTURE.md).
- State is in memory, resets on server restart, and is not synchronized between
  tabs. There are no accounts, persistence, or public deployment. JavaScript is
  required. On a draft network error, text stays in the editor; restore the
  connection and retry Apply. If initial connection fails, restart the server
  and reload the page.
- Tests emit one recorded Starlette/HTTPX deprecation warning. Browser checks
  used Edge and Chromium on Windows; other browsers/platforms and manual
  screen-reader use have not been verified.

## MVC reflection

MVC helped make state ownership explicit. The model owns applied source, drafts,
revisions, results, and busy state, so rules such as blocking tools during
unapplied edits can be tested without HTTP or a browser. This also prevents the
interface from being the only place that protects application state. The view
renders text and forwards interactions, while the controller coordinates source
changes and calls the language backend.

The most difficult separation was handling asynchronous work without mixing
transport concerns into the model. Language operations use a synchronous
interface, but interpretation must not block browser requests. The controller
therefore runs backend work in a thread, while the bounded adapter manages a
separate worker process. Request ownership matters: cancelling an HTTP wait must
not release busy state while evaluation is still running. Matching completion
and cleanup to the original operation request keeps that rule inside the model.

Draft synchronization was another boundary challenge. The browser must preserve
newer typing when an older response arrives, but it should not decide whether a
program is valid LAMBDA. Serialized draft requests and literal rendering handle
presentation concerns; transport validation belongs to shared validation code,
and constructor validation belongs to the language adapter.

A future type checker could replace one backend method while retaining the same
result metadata and view. A compiler would require additional model support for
revision-associated artifacts and invalidation, followed by an executor that
consumes the stored artifact. The existing contracts identify those changes
without pretending that compilation or generated-code execution already works.
