# Assignment 6: Extended LAMBDA to Pure Lambda Calculus

## Current status

Steps 1–2 provide the Python package, source-AST adapter, immutable target terms,
printing, name analysis, deterministic fresh names, capture-avoiding substitution,
and alpha-equivalence checking. The compiler, shared evaluator, encodings,
observers, and demo are not implemented yet. Passing these tests does not
establish compiler correctness.

The assignment is authoritative: [Assign06.md](../Assign06.md).
See [OBJECTIVES.md](OBJECTIVES.md) for the component overview and
[CHECKLIST.md](CHECKLIST.md) for planned verification and milestone tracking.

## Setup and tests

Use **Python 3.12 or later**. No third-party packages or installation steps are
required. Run these commands from `assigns/06/`:

```powershell
python --version
python -B -m unittest discover -s MySolution/tests -t . -v
```

`-B` prevents bytecode-cache writes, including beside the supplied Assignment 5
file. The package also ignores local bytecode caches and virtual environments.

Step 1 verification on Python 3.14.7: all **4 setup tests passed**. The source-AST
example below produced the documented output, and the supplied file's SHA-256
hash was unchanged before and after this milestone.

Step 2 verification on Python 3.14.7: all **27 tests passed** (4 setup and 23 target
operation tests, several with additional subcases).

The adapter requires the repository's existing `assigns/05/lambda1_vp.py` in
its original relative location. It loads that exact file by location without
changing the module search path or modifying the supplied code. All solution
modules will access its classes through `MySolution.source_ast.ast`.

## Source-AST example

From `assigns/06/`, run `python -B` and enter:

```python
from MySolution.source_ast import ast

expression = ast.D0Eop2("+", ast.D0Eint(2), ast.D0Eint(3))
print(expression)
```

Expected output:

```text
D0Eop2(name='+', arg1=D0Eint(arg1=2), arg2=D0Eint(arg1=3))
```

This constructs syntax for `2 + 3`; it does not execute the program. The output
is the supplied dataclass representation, not our future source or target printer.

## Target terms and operations

`target.py` defines exactly three target node forms. They are frozen dataclasses:
their fields cannot be reassigned, so operations return terms rather than editing
existing trees. Identifier names follow `[A-Za-z_][A-Za-z0-9_]*`.

| Interface | Meaning |
| --- | --- |
| `Var(name)` | Variable reference |
| `Lam(name, body)` | Single-parameter function |
| `App(fn, arg)` | Function application |
| `pretty(term)` | Required fully parenthesized target notation |
| `free_vars(term)` | Immutable set of free variable names |
| `all_names(term)` | Immutable set including variable uses and all binders |
| `FreshNameGenerator(reserved_names).fresh(base)` | A deterministic unused identifier |
| `substitute(term, variable, replacement)` | Capture-avoiding replacement of free uses, without evaluation |
| `alpha_equivalent(left, right)` | Same binding structure, with identical free variable names |

For example, in the same Python session or a new `python -B` session:

```python
from MySolution.target import Lam, Var, alpha_equivalent, free_vars, pretty, substitute

original = Lam("y", Var("x"))
result = substitute(original, "x", Var("y"))
print(pretty(original))
print(pretty(result))
print(sorted(free_vars(result)))
print(result == Lam("fresh", Var("y")))
print(alpha_equivalent(result, Lam("fresh", Var("y"))))
```

Expected output:

```text
(lam y. x)
(lam y_1. y)
['y']
False
True
```

`==` compares names and structure exactly. `alpha_equivalent` instead tracks the
nearest enclosing binder for each bound occurrence. This handles repeated binder
names without confusing bound occurrences with free variables of the same name.

### Fresh-name policy

Each generator copies the supplied reserved-name collection and starts its
counter at 1. `fresh("y")` tries `y_1`, `y_2`, and so on. Every attempted candidate
advances the counter, even if already reserved; all bases share that counter.
Returned names are immediately reserved too.

Each substitution creates its own generator, reserving **all** names in both
input terms plus the variable being replaced. This includes unused binders, not
just free names. It renames a binder only when substitution actually enters its
body and capture would otherwise occur. Repeating the same substitution produces
the same result, independent of earlier calls.

Substitution may return unchanged immutable subterms or insert the replacement
directly. Sharing those nodes is safe because they cannot be reassigned. It never
evaluates or recursively substitutes into an inserted replacement. Structural
operations do traverse lambda bodies; that is distinct from evaluating them.

These structural helpers use recursive tree traversal. Extremely deeply nested
terms can reach Python's recursion limit; this milestone does not implement a
stack-independent traversal or an evaluator. Constructor child shapes are assumed
valid; the module is not a general AST validator.

## Architecture

| Component | Module | Responsibility | Status |
| --- | --- | --- | --- |
| Source integration | `source_ast.py` | Load the supplied AST and visitor interface once | Implemented |
| Source helpers | `source_ops.py` | Printing and source name analysis | Planned |
| Target terms and operations | `target.py` | Immutable `Var`, `Lam`, `App`; printing, names, substitution, alpha-equivalence | Implemented |
| Shared evaluator | `evaluator.py` | Execute source and target syntax through one engine | Planned |
| Church encodings | `encodings.py` | Construct closed pure terms for data and operations | Planned |
| Compiler | `compiler.py` | Translate using `D0ExpVisitor`; never evaluate input | Planned |
| Observers | `observers.py` | Decode expected data kinds through bounded target contexts | Planned |
| Demonstrations | `demo.py` | Run and report the required end-to-end examples | Planned |
| Tests | `tests/` | Setup and target-operation tests; remaining features added incrementally | In progress |

The intended pipeline is:

```text
Source AST --------------------> shared evaluator ----> source result
    |
    +--> compiler --> target AST --> shared evaluator --> target value
                                                            |
                                                      bounded observer
                                                            |
                                                       decoded result
```

For terminating examples, compare source and decoded target results against
explicit expected answers. Divergent examples will run only through bounded
target execution, avoiding an unbounded source evaluation.

The compiler will depend on source/target syntax and encoding builders, not on
the evaluator. The evaluator will not import or invoke the compiler. Observers
will build pure target contexts and use the same evaluator.

## Planned execution and observation contracts

Target execution will use weak, left-to-right call-by-value reduction and count
only beta-value steps. Observation will have its own budget and count, including
pair projections and recursively observed components. Completion, exhaustion,
and malformed observations will remain distinguishable.

The initial planned demo defaults are 100,000 execution steps and 100,000
observation steps per example. These are not measured requirements or verified
sufficient budgets yet; finalize them after running the terminating examples.
Compilation will support open expressions. Target execution will initially
require closed terms and report open inputs clearly.

## Commands and deliverables still pending

The planned demo command is `python -B -m MySolution.demo`. It is **not available
in Step 2**. A later milestone will add its exact options and output details.

`DESIGN.md`, PDF presentation slides, and the 15–20 minute face-visible recording
are pending. Their actual files or recording link will be identified here when
they exist. A parser, web interface, and static type checker are outside the
required implementation.

## Attribution

Source AST classes and the visitor interface come from the instructor-supplied
Assignment 5 `lambda1_vp.py`, used unchanged. Its existing free-variable visitor
is used in setup tests. Its interpreter is not used to execute assignment
programs: Assignment 6 requires its own shared evaluator and different operator
semantics.

The `FreshNameGenerator` policy and scoped binder-renaming approach in `target.py`
adapt the student's Assignment 5 `MySolution/operations.py`. The target nodes,
operations, and alpha-equivalence checker are implemented separately for this
assignment. No external Church-encoding implementation has been used yet.

See [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md) for AI assistance and verification.
