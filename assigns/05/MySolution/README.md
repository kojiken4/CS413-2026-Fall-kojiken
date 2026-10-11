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
9.1.1: 17 unittest tests and 94 pytest tests passed, each command exiting with 0.
The unittest constructor and helper tests use subtests; pytest runs each example
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

## Substitution example

```python
from lambda1_vp import D0Elam, D0Eop2, D0Evar
from MySolution.operations import d0exp_pretty, d0exp_substitute

expression = D0Elam("y", D0Eop2("+", D0Evar("x"), D0Evar("y")))
result = d0exp_substitute(expression, "x", D0Evar("y"))
print(d0exp_pretty(result))
```

Output:

```text
(lam y_1. (y + y_1))
```

The binder is renamed before insertion, keeping the replacement's `y` free.
Only free occurrences of the target are replaced. Substitution stops in a body
where the target is bound, and let initializers are always processed separately.
The replacement is inserted directly without substituting inside it. Neither
input AST is mutated, and unchanged subtrees may be shared with the result.

## Name and renaming helpers

`AllNamesVisitor` returns a `frozenset[str]` containing every variable occurrence
and binder declaration, including unused binders. Operator names are not variable
names. All expression forms dispatch through `accept`.

`ScopedRenameVisitor(old_name, new_name)` returns an expression with free
occurrences of `old_name` renamed within the region passed to it. It leaves
nested binder declarations unchanged and stops in bodies where a lambda or
either `fix` binder shadows `old_name`. A `let` initializer is always visited;
its body is left alone when its bound name shadows `old_name`.

The caller must supply a globally fresh `new_name`. To alpha-rename a binder,
the caller applies this visitor to that binder's body and separately updates
the outer declaration. This helper alone does not perform substitution.

## Fresh-name policy

`FreshNameGenerator` copies its reserved-name set and starts one counter at 1.
For a binder named `y`, it tries `y_<counter>`, advancing the counter on every
attempt, including collisions. Accepted names are immediately reserved. The
same counter is shared across binder names: without collisions, requests for
`y`, `y`, and `f` produce `y_1`, `y_2`, and `f_3`.

`d0exp_substitute` initializes one generator per call with all names collected
from the original expression and replacement, plus the target. All recursive
substitution within that call shares that generator.
For example, if `y_1`, `y_2`, and `y_3` are reserved, the first fresh name for
`y` is `y_4`. A new generator starts numbering over, making repeated calls
deterministic.

Children are visited in constructor order, with a let initializer processed
before its body. Distinct fix binders are considered in function-name-then-
parameter order. When fix binder names are equal, a conflict produces one fresh
name for both declarations, preserving parameter shadowing. Binders are not
renamed when no substitution can occur in their body.

## Current implementation

Pretty printing is implemented through `PrettyPrintVisitor`, whose result type
is `str`. Every child expression dispatches through `accept`.
The name-collection and scoped-renaming visitors and fresh-name generator are
implemented and tested. They preserve input ASTs and do not evaluate expressions.
Capture-avoiding substitution is implemented through `SubstitutionVisitor`, whose
result is an expression. It carries the target, replacement, replacement's free
variables, and shared fresh-name generator. The public entry point initializes
this context; direct visitor callers must reserve all input names and the target
in their generator. The required 300–500-word design explanation will be added
when documentation is finalized.
