# LAMBDA Web Front-End

Assignment 04 implementation, currently at Step 3 (language-tool backend).
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
recursion limits as input errors. Upload-byte decoding will be implemented with
the HTTP workflow; the current reader accepts already-decoded text.

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
interpret source. Applied-source and UI prerequisites will be enforced in later
steps. See `ARCHITECTURE.md` for the replaceable interface and future artifact
contract.

### Sample inputs

| File | Lint | Interpret |
| --- | --- | --- |
| `samples/factorial.txt` | Pass | `D0Vint(arg1=120)` for factorial(5) |
| `samples/fibonacci.txt` | Pass | `D0Vint(arg1=8)` for Fibonacci(6) |
| `samples/open-variable.txt` | Undeclared `x` | Runtime error sentinel |
| `samples/division-by-zero.txt` | Pass | Division-by-zero runtime error |
| `samples/invalid-input.txt` | Invalid input | Invalid input |

## Current limitations and remaining work

The landing page, restricted reader, and synchronous backend are implemented.
The supplied `lambda1.py` is unchanged. Backend operations are tested directly
but are not connected to browser requests. Source editing and revision state
are not implemented; the caller currently supplies the revision identifier.

The next steps add model state rules, bounded execution, HTTP workflows, and
browser controls. The five-second backend timeout is planned, not yet implemented:
do not use this synchronous adapter for unbounded programs. Type-check/Compile
remain placeholders and generated-code execution will remain unavailable.

Required browser demonstrations, final limitations, and the 200-300 word MVC
reflection will be completed after the features are tested.
