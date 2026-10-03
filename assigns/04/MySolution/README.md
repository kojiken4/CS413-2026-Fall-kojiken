# LAMBDA Web Front-End

Assignment 04 implementation, currently at Step 6 (HTTP controller integration).
Requires Python 3.12 or later; setup and tests were verified with Python 3.13.14 on Windows.
Direct runtime dependencies are pinned in `requirements.txt`; test dependencies
are in `requirements-dev.txt`.

## Setup

Run these PowerShell commands from the repository root:

```powershell
Set-Location assigns/04/MySolution
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Activation is unnecessary. The environment and caches are ignored by Git.

## Start

From `MySolution`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn lambda_web.app:create_app --factory --host 127.0.0.1 --port 8000 --workers 1
```

Open [the local application](http://127.0.0.1:8000/). Stop the server with Ctrl+C.
The server must remain on the loopback interface with one worker.

## Test

From `MySolution`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Constructor-input format

`lambda_web.constructor_reader.read_constructor(source)` accepts one constructor
expression and returns a supplied `lambda1.d0exp`. Input is data, not a script.
No imports are needed in constructor input. Examples:

```python
D0Eop2("+", D0Eint(20), D0Eint(22))
D0Eint(arg1=-42)
D0Epair(arg2=D0Ebtf(False), arg1=D0Eint(+1))
```

Supported constructors: `D0Eint`, `D0Ebtf`, `D0Evar`, `D0Eop1`, `D0Eop2`,
`D0Elam`, `D0Efix`, `D0Eapp`, `D0Eif0`, `D0Elet`, `D0Epair`, `D0Epfst`,
and `D0Epsnd`. Arguments follow the supplied dataclass signatures. Positional,
named, and mixed arguments are accepted; names must match the fields exactly.
Missing, extra, unknown, or duplicate arguments are rejected.

Nested constructors, comments, multiline expressions, strings, booleans, and
signed integer literals are accepted. Scalar field types are checked exactly:
`True` is not an integer and `1` is not a boolean. Operator names are strings;
the reader does not check whether evaluation supports an operator.

Only allowlisted constructor calls and their expected literals are accepted.
Statements, arbitrary Python calls, attributes, arithmetic outside constructors,
comprehensions, formatted strings, and `*`/`**` expansion are rejected. The reader
uses Python's AST parser and never executes source or evaluates LAMBDA.
Invalid input raises `ConstructorInputError` with a diagnostic.

Source must be nonempty UTF-8 text of at most **65,536 bytes (64 KiB)**, including
comments and whitespace. The reader reports parser nesting limits or Python
recursion limits as input errors. Uploads are decoded strictly as UTF-8 by the
controller; the reader accepts already-decoded text.

## Language-tool backend

`LambdaBackend` in `lambda_web/backend.py` provides `lint(source, revision)`,
`interpret(source, revision)`, `typecheck(source, revision)`,
`compile(source, revision)`, and `execute(artifact, revision)`.
Each returns an `OperationResult` containing operation, source revision, outcome,
and textual output. Lint additionally returns a `frozenset` of free variables.

Lint uses the supplied `d0exp_fvset` without evaluation. Open expressions produce
a language error with sorted undeclared names. Interpret independently calls
`d0exp_evaluate` with an empty environment. Successful output is the returned
value as text; input errors, runtime errors, and unexpected backend failures have
distinct outcomes. An exact `D0V000()` directly or inside a pair is a runtime error.

Type-check and Compile return `not_implemented`, without parsing source or
producing artifacts. Execute returns `unavailable`; it does not compile or
interpret source. Applied-source, dirty, and busy prerequisites are enforced by
the model through HTTP routes. See `ARCHITECTURE.md` for the future artifact
contract.

### Sample inputs

| File | Lint | Interpret |
| --- | --- | --- |
| `samples/factorial.txt` | Pass | `D0Vint(arg1=120)` for factorial(5) |
| `samples/fibonacci.txt` | Pass | `D0Vint(arg1=8)` for Fibonacci(6) |
| `samples/open-variable.txt` | Undeclared `x` | Runtime error sentinel |
| `samples/division-by-zero.txt` | Pass | Division-by-zero runtime error |
| `samples/invalid-input.txt` | Invalid input | Invalid input |

## Execution bounds

`BoundedBackend` in `lambda_web/bounded_backend.py` implements the same backend
interface, launching a fresh trusted Python worker for each Lint or Interpret.
Source is JSON data on standard input, not part of a shell command. UTF-8 JSON
results are validated and free-variable lists are reconstructed as `frozenset`.
Type-check/Compile/Execute responses stay unchanged and launch no worker.

The default worker timeout is **five seconds**, covering worker startup, imports,
constructor parsing, language processing, and result transport after OS process
creation. OS process creation itself cannot always be interrupted, so total
elapsed time can include that overhead and process cleanup. Timed-out workers
are killed and waited for; their pipes are closed. Timeouts, crashes, invalid
responses, and communication failures return `backend_failure`, distinct from
constructor input errors and language runtime errors.

The source limit remains **64 KiB UTF-8**. The supplied recursive evaluator can
also reach Python's recursion limit, which is reported as a runtime error.
The bounded adapter does not change interpreter semantics or implement generated
code execution. `LambdaBackend` remains the in-process implementation used by
the worker and direct language tests; it has no standalone execution timeout.

The backend interface is synchronous. The controller runs actions using
`asyncio.to_thread`, so waiting does not block the event loop. Model work starts
with `begin_operation`; completion and cleanup use the same request. Cancelling
an HTTP wait does not cancel its worker or release busy state prematurely.
Application shutdown waits for controller-owned work. Tests cover timeout
recovery, HTTP responsiveness, preserved source, and successful retry.

## HTTP workflows

The landing page still has no interactive controls; Step 7 will connect the
browser to these implemented routes. JSON field names are shown below.

| Method | Route | Input / behavior |
| --- | --- | --- |
| GET | `/api/state` | Current model snapshot |
| POST | `/api/source/draft` | JSON `source` string; retain editable text |
| POST | `/api/source/manual` | Open a blank manual draft |
| POST | `/api/source/apply` | Validate and apply draft |
| POST | `/api/source/discard` | Restore applied source |
| POST | `/api/source/canned` | JSON `name`: `factorial` or `fibonacci` |
| POST | `/api/source/upload` | Multipart `file`: local UTF-8 text |
| POST | `/api/actions/{operation}` | `lint`, `interpret`, `typecheck`, `compile`, or unavailable `execute` |

Source routes return a state snapshot. Action responses contain `state` and
`result`, including operation, source revision, outcome, output, free variables,
and a null artifact. JSON transports output literally and preserves line breaks;
browser rendering remains to be implemented.

Invalid source returns HTTP 400, model conflicts 409, and invalid request fields
422, with `detail` and unchanged applied `state`. Unknown canned names return
404. Language/tool outcomes return HTTP 200 with their distinct result outcome.
Rejected text edits and empty uploads remain correctable drafts. Undecodable or
oversized uploads preserve the existing draft as well as applied state, rather
than substituting an incomplete file prefix. Uploads are read to at most 65,537
bytes for the application size check and closed after handling; multipart parsing
may spool uploaded data before this check. Original local files are never edited.

`create_app(model=..., backend=...)` supports independent state and a replacement
backend without changing the view. The default backend is `BoundedBackend`.

## Application model

`ApplicationModel` owns an immutable `ApplicationState` snapshot with applied
source/name, draft/name, revision, operation results, artifact availability, and
active operation. It uses only shared contracts and transport validation, not
FastAPI, browser code, the constructor reader, or the interpreter.

- `start_manual_input` opens a blank draft without replacing applied source;
  `set_draft` keeps edits, including invalid text, available for correction.
- `apply_changes` validates and applies edited text. `discard_changes` restores
  the applied text/name without changing its revision or results.
- `load_source` accepts already-decoded uploads or canned inputs. Accepted loads
  and edits increment the revision and clear results/artifacts. Invalid loads
  preserve applied state and retain rejected text as a correctable draft.
- Dirty state blocks actions and replacement. Busy state also blocks editing,
  Apply, and Discard. Source operations require applied source; Execute remains
  unavailable because no generated code exists.
- `begin_operation` returns the request containing applied text and revision.
  `finish_operation(request, result)` records matching results and releases busy
  state. Controller cleanup must call `abort_operation(request)` if needed.
  Cleanup and late completion from an older request cannot affect newer work.

Malformed constructor syntax can be applied; the backend reports its input error
when Lint/Interpret runs. The model checks transport validity, not language syntax.
Source names are labels; the model never reads or modifies the original file.

## Current limitations and remaining work

The landing page, reader, model, bounded backend, and HTTP controller are
implemented and tested. The supplied `lambda1.py` is unchanged. Real loopback
requests verified server responsiveness during interpretation and timeout/retry.
Browser controls and visual recovery checks remain for Step 7.

Type-check/Compile remain placeholders. No generated artifacts are created or
accepted by this model version; Execute stays unavailable. Artifact support is
reserved for future development, not implemented as an assignment extension.

Required browser demonstrations, final limitations, and the 200-300 word MVC
reflection will be completed after the features are tested.
