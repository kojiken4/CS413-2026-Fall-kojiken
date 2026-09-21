# Assignment 02

## Goal

Extend the LAMBDA0 interpreter with pairs and projections, then translate an
ATS2 eight-queens solver into a LAMBDA0 term executed by the interpreter.

## Current status: baseline

`lambda0.py` is an unchanged copy of the assignment starter.
`TEST/test01_lambda0.py` is an unchanged copy of the supplied regression tests.
Pair support and the queens translation are not implemented yet.

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
