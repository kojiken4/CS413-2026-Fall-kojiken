# Assignment 05

Requires Python 3.12 or later. The local verification interpreter is Python
3.14.7. This solution imports the supplied `lambda1_vp.py` without modifying it.

## Setup

Run all commands from the assignment directory, `assigns/05`.
Create an isolated environment and install pytest:

```powershell
python -m venv MySolution/.venv
./MySolution/.venv/Scripts/python.exe -m pip install pytest
```

## Run the suites independently

Run the standard-library unittest suite:

```powershell
./MySolution/.venv/Scripts/python.exe -B -m unittest discover -s MySolution -t . -p "test_unittest.py" -v
```

Run only the pytest-style suite:

```powershell
./MySolution/.venv/Scripts/python.exe -B -m pytest MySolution/test_pytest.py -q -o cache_dir=MySolution/.pytest_cache
```

The unittest suite uses `unittest.TestCase`; the pytest suite uses independent
test functions with plain assertions. Neither suite depends on the other.
The `-B` option prevents Python bytecode caches, including beside the supplied
interpreter. The environment and pytest cache are excluded from version control.

Both test commands were verified from `assigns/05` on Python 3.14.7 with pytest
9.1.1: 2 unittest tests and 2 pytest tests passed, each command exiting with 0.

## Current implementation

The package and both suites currently verify imports and dispatch through the
supplied Visitor interface. Pretty printing and substitution are not yet
implemented. Operation examples, the fresh-name policy, known limitations, and
the required 300–500-word design explanation will be documented with the
corresponding implementation steps.
