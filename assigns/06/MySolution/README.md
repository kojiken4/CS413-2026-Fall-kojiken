# Assignment 6: Extended LAMBDA to Pure Lambda Calculus

## Current status

Step 1 establishes the Python package, source-AST adapter, and test discovery.
The compiler, target terms, shared evaluator, encodings, observers, and demo
are not implemented yet. Passing the setup tests does not establish compiler
correctness.

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

## Architecture

| Component | Module | Responsibility | Status |
| --- | --- | --- | --- |
| Source integration | `source_ast.py` | Load the supplied AST and visitor interface once | Implemented |
| Source helpers | `source_ops.py` | Printing and source name analysis | Planned |
| Target terms and operations | `target.py` | Immutable `Var`, `Lam`, `App`; printing, names, substitution | Planned |
| Shared evaluator | `evaluator.py` | Execute source and target syntax through one engine | Planned |
| Church encodings | `encodings.py` | Construct closed pure terms for data and operations | Planned |
| Compiler | `compiler.py` | Translate using `D0ExpVisitor`; never evaluate input | Planned |
| Observers | `observers.py` | Decode expected data kinds through bounded target contexts | Planned |
| Demonstrations | `demo.py` | Run and report the required end-to-end examples | Planned |
| Tests | `tests/` | Setup checks now; feature and regression tests as implemented | In progress |

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
in Step 1**. A later milestone will add its exact options and output details.

`DESIGN.md`, PDF presentation slides, and the 15–20 minute face-visible recording
are pending. Their actual files or recording link will be identified here when
they exist. A parser, web interface, and static type checker are outside the
required implementation.

## Attribution

Source AST classes and the visitor interface come from the instructor-supplied
Assignment 5 `lambda1_vp.py`, used unchanged. Its existing free-variable visitor
is used in setup tests. Its interpreter is not used to execute assignment
programs: Assignment 6 requires its own shared evaluator and different operator
semantics. Record any later adaptations of Assignment 5 solution code or external
encoding references when introduced.

See [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md) for AI assistance and verification.
