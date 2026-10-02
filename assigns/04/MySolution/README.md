# LAMBDA Web Front-End

Assignment 04 implementation, currently at Step 1 (application foundation).
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

## Current limitations and remaining work

Only the landing page is implemented. The supplied `lambda1.py` is copied
unchanged into the application package. There is no source reader, editing,
action dispatch, or generated-code execution yet.

The next steps add the restricted constructor reader, real Lint/Interpret,
source revision rules, bounded execution, HTTP workflows, and browser controls.
Type-check and Compile will remain explicit placeholders and Execute disabled.
The planned source limit is 64 KiB of UTF-8 and the planned backend timeout is
five seconds; neither bound is implemented at this stage.

Required demonstrations, supported input details, final limitations, and the
200-300 word MVC reflection will be completed after the features are tested.
