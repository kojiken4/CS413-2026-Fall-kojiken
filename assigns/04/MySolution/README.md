# LAMBDA Web Front-End

Assignment 04 implementation, currently at Step 2 (restricted constructor reader).
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

## Current limitations and remaining work

The landing page and restricted reader are implemented. The supplied `lambda1.py`
is unchanged. The reader is not connected to the browser or language operations
yet. Source editing, revision state, action dispatch, and generated-code execution
are not implemented.

The next steps add real Lint/Interpret, source revision rules, bounded execution,
HTTP workflows, and browser controls. Type-check and Compile will remain explicit
placeholders and Execute disabled. The five-second backend timeout is planned,
not yet implemented.

Required demonstrations, final limitations, and the 200-300 word MVC reflection
will be completed after the features are tested.
