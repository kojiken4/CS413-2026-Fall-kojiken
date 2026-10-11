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
9.1.1: 8 unittest tests and 23 pytest tests passed, each command exiting with 0.
The unittest constructor test uses subtests; pytest runs each constructor example
as a separate parameterized test, so the reported test counts differ.

## Pretty-printing example

From `assigns/05`, run this Python code using the local environment:

```python
from lambda1_vp import D0Eapp, D0Elam, D0Eop2, D0Evar, D0Eint
from MySolution.operations import d0exp_pretty

expression = D0Eapp(
    D0Elam("x", D0Eop2("+", D0Evar("x"), D0Eint(1))),
    D0Eint(4),
)
print(d0exp_pretty(expression))
```

Output:

```text
((lam x. (x + 1)) 4)
```

`d0exp_pretty` returns a string without a final newline; `print` adds the displayed
newline. It supports every supplied expression constructor and preserves input
ASTs. Operators and names are printed literally, without evaluation or input
validation.

## Current implementation

Pretty printing is implemented through `PrettyPrintVisitor`, whose result type
is `str`. Every child expression dispatches through `accept`.
Capture-avoiding substitution is not yet implemented. Its examples, fresh-name
policy, and the required 300–500-word design explanation will be documented
with the corresponding implementation steps.
