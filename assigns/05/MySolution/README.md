# Assignment 05

Requires Python 3.12 or later. The local verification interpreter is Python
3.14.7. This solution imports the supplied `lambda1_vp.py`.

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
9.1.1: 22 unittest tests and 150 pytest tests passed, each command exiting with 0.
The unittest constructor and helper tests use subtests; pytest runs each example
as a separate parameterized test, so the reported test counts differ.

## Pretty-printing example

From `assigns/05`, start the local Python interpreter with
`./MySolution/.venv/Scripts/python.exe -B`, then run the following Python code:

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

Run this example in the same interpreter:

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

## Design explanation

The supplied expression classes represent syntax, while visitors implement
operations on that syntax. Each expression's `accept` method selects the matching
visitor method. Every recursive traversal in the solution uses this dispatch,
including name collection and renaming. The interpreter and expression classes
remain unchanged.

The visitor interface is generic in its result type. `PrettyPrintVisitor` returns
`str`, `AllNamesVisitor` returns `frozenset[str]`, and the renaming and substitution
visitors return expressions. Pretty printing recursively combines child strings
with the required punctuation and spaces. It never evaluates an operator, so
division-by-zero syntax can be printed safely. Name collection includes binder
declarations even when no occurrence uses them, which prevents fresh names from
colliding with existing bound names.

`d0exp_substitute` initializes context for one substitution: the target variable,
replacement expression, replacement's free variables, and a fresh-name generator.
The generator reserves names from both input trees and the target. One visitor
shares this context throughout the traversal, while each public call creates a
new generator. A matching variable returns the replacement directly, without
traversing it. Other nonbinding forms rebuild their children and preserve their
constructors and operators. Input fields are never assigned, and unchanged
subtrees may be reused.

Binding methods first determine whether substitution can occur in their bodies.
A lambda binds its parameter; a fix binds its function name and parameter. A let
binds only in its body, so its initializer is always processed separately. When a
binder conflicts with the replacement's free variables, substitution generates a
fresh name and applies `ScopedRenameVisitor` to the body before insertion. The
helper changes occurrences belonging to that outer scope, stopping where nested
binders shadow the old name. The caller updates the outer declaration. Equal fix
names receive the same fresh name, preserving parameter shadowing.

Adding an operation requires a new visitor implementing every existing visit
method, but no edits to expression classes. Adding an expression constructor
would instead require its class and dispatch method, a corresponding method in
the visitor interface, and support in each existing visitor. This design makes
new operations local while spreading constructor additions across operations.
The separate unittest and pytest suites verify explicit outputs and AST
structures; they share examples without depending on each other's tests.

## Known limitations and verification status

- Inputs are assumed to be valid supplied ASTs with the identifier syntax stated
  in the assignment. Input validation is not implemented.
- Traversals are recursive and subject to Python's recursion limit for deeply
  nested expressions.
- Results may share unchanged subtrees and the replacement with the inputs.
  Input preservation during the operation does not imply an independent deep copy.
- Direct use of `ScopedRenameVisitor` requires a globally fresh new name. Direct
  use of `SubstitutionVisitor` requires a generator reserving all names from both
  inputs and the target; `d0exp_substitute` performs this setup automatically.

Both suites cover the assignment's testing requirements with explicit outputs
or expected ASTs:

| Requirement | Coverage in each suite |
| --- | --- |
| Exact printing | Every constructor, nested expressions, signed and large integers, both booleans |
| Substitution traversal | Every constructor, matching/nonmatching variables, replacement containing the target |
| Binding and shadowing | Lambda, let, both fix binders, and equal-name fix binders |
| Capture avoidance | Lambda, let, either fix binder, and both distinct fix binders together |
| Nested scopes and freshness | Nested lambda/let/fix shadowing, original/replacement bound-name collisions, target collisions, names shared across one call |
| Let scope | Initializers processed separately from bodies, including nested initializers under an outer binder |
| Preservation and determinism | Independent snapshots of both inputs, repeated-call structural equality, guarded no-evaluation checks |
| Free-variable properties | Target present and absent, paired with structural or exact-output checks |

The tests verify the stated examples and edge cases; passing tests are not a
formal proof for every possible input AST.