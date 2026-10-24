# Assignment 6: Extended LAMBDA to Pure Lambda Calculus

## Current status

Steps 1–5 provide the Python package, source-AST adapter, immutable target terms,
printing, name analysis, deterministic fresh names, capture-avoiding substitution,
alpha-equivalence checking, and one shared evaluator for source and target
programs. Basic Church numerals, booleans, identity, and bounded natural/boolean
observers are implemented. Encoded operations, pairs, Z, compilation, and the demo
are still pending. Passing these tests does not establish compiler correctness.

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

Step 3 verification on Python 3.14.7: all **46 tests passed**, including 19 new
target-evaluation tests.

Step 4 verification on Python 3.14.7: all **84 tests passed**, including 38 new
source and engine-boundary tests. Source factorial of 4 returns 24 and Fibonacci
of 5 returns 5. All existing target budget/count tests still pass.

Step 5 verification on Python 3.14.7: all **112 tests passed**, including 8 basic
encoding tests and 20 scalar-observation tests. Existing suites remain unchanged.

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
is the supplied dataclass representation; the target printer handles target
terms, and a source printer is still planned.

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

## Target evaluation

`evaluate(expression, max_steps=...)` in `evaluator.py` executes closed target
terms. The same engine also evaluates source ASTs, as described below; the
supplied Assignment 5 interpreter is not used.

Evaluation is **weak**: a lambda completes as a value without running its body.
Applications evaluate the function, then the argument, then substitute the
argument value into the function body. Even an argument that the function ignores
must finish first. There is no reduction beneath lambdas and no eta reduction.

The engine uses a loop and a stack of continuation frames. A frame records work
waiting for the current expression: either an argument waiting for its function,
or a function value waiting for its argument. This avoids one Python call frame
per reduction. Name analysis and substitution still use recursive tree traversal,
so the deep-input limitation documented above remains.

For target calls, the returned immutable `EvaluationResult` has these
fields/properties:

| Name | Meaning |
| --- | --- |
| `status` | `"completed"` or `"exhausted"` |
| `term` | Completed lambda, or the whole unfinished term with its surrounding applications restored |
| `value` | Completed lambda; `None` on exhaustion |
| `steps` | Number of beta-value contractions actually performed |
| `budget` | The supplied `max_steps` |

Only a beta-value contraction consumes a step. Traversing applications or moving
between continuation frames does not. A lambda completes in zero steps even with
a zero budget. A value reached on the final allowed step counts as completed.
Exhaustion means another contraction is needed; it does not prove nontermination.
An unfinished term can be passed to `evaluate` again with a new budget; the new
call reports only its own step count.

For example, after starting `python -B` from `assigns/06/`:

```python
from MySolution.evaluator import evaluate
from MySolution.target import App, Lam, Var, pretty

identity = Lam("x", Var("x"))
term = App(App(identity, identity), App(identity, identity))
for budget in range(4):
    result = evaluate(term, max_steps=budget)
    print(budget, result.status, result.steps, pretty(result.term))
```

Expected output:

```text
0 exhausted 0 (((lam x. x) (lam x. x)) ((lam x. x) (lam x. x)))
1 exhausted 1 ((lam x. x) ((lam x. x) (lam x. x)))
2 exhausted 2 ((lam x. x) (lam x. x))
3 completed 3 (lam x. x)
```

### Execution input errors

- A negative budget raises `ValueError`.
- A noninteger budget, including a boolean, raises `TypeError`.
- A term with free variables raises `OpenTermError` (a `ValueError` subclass),
  listing those names in sorted order. This restriction also applies to a lambda
  with free variables in its body, even though that body would not execute yet.
- Structural operations and substitution still accept open terms. The closed-term
  restriction applies only to execution, and the future compiler must support
  open expressions too.

## Source evaluation

### High-level purpose

Source execution establishes a baseline for checking the future compiler. Run
an original program with the shared engine, then later run and observe its
compiled target term. Both results must agree with the explicit expected answer.
The compiler itself must never obtain an answer by running source code.

The engine implements every required source constructor and operator. Source
arithmetic may use Python arithmetic because numbers and operations are built
into the source language. Target execution still operates only on target syntax
through substitution and never calls the source arithmetic helpers.

### Interface and values

Call `evaluate(source_expression)` without `max_steps`. It returns the same
`EvaluationResult` structure, with `status == "completed"` and both `term` and
`value` referring to a source value. `steps` and `budget` are `None`: source
execution does not claim zero target steps or provide a finite execution limit.
Passing a non-None source budget raises `TypeError` rather than silently ignoring
it. Use source evaluation only for terminating examples; divergent examples will
be compiled and run with a target budget.

The source values reuse the supplied record classes:

| Value | Meaning |
| --- | --- |
| `D0Vint(n)` | Natural number, available as `.arg1` |
| `D0Vbtf(b)` | Boolean, available as `.arg1` |
| `D0Vpair(left, right)` | Evaluated components in `.arg1` and `.arg2` |
| `D0Vlam(env, expression)` | Ordinary closure with its defining environment |
| `D0Vfix(env, expression)` | Recursive closure with its defining environment |

For example, from `assigns/06/` in `python -B`:

```python
from MySolution.evaluator import evaluate
from MySolution.source_ast import ast

expression = ast.D0Eop2(
    "+", ast.D0Eint(2), ast.D0Eop2("*", ast.D0Eint(3), ast.D0Eint(4))
)
result = evaluate(expression)
print(result.status, result.value.arg1, result.steps, result.budget)
print(evaluate(ast.D0Eop2("-", ast.D0Eint(2), ast.D0Eint(5))).value.arg1)
```

Expected output:

```text
completed 14 None None
0
```

### Closures and shared control flow

A closure pairs function syntax with the environment where it was defined.
The environment is an immutable linked chain of bindings; lookup selects the
nearest matching name. Calling a source function extends its defining environment
with the argument, rather than extending the caller's environment. For example,
a function created with `x = 3` still uses three if its caller later binds `x = 99`.

A recursive call first binds the function name to the same recursive closure,
then binds the parameter to the argument. Adding the parameter last makes it
shadow the function name when both names coincide. Creating either kind of
closure does not evaluate its body. This implements built-in source recursion;
the pure target Z encoding and recursive compilation are still planned for Step 8.

Both languages share the evaluation loop, variable/application dispatch, value
delivery, and continuation stack. Source frames add lets, conditionals, operators,
pairs, and projections. Frames save the surrounding environment before evaluating
a subexpression, so its temporary bindings do not leak into a sibling expression.
Target application performs substitution; source application enters a closure's
environment. No call delegates to the supplied interpreter or a second source
evaluator.

Source conditionals evaluate only the selected branch. `and` skips the right
operand when the left is false; `or` skips it when the left is true. Function
arguments, let initializers, arithmetic/comparison operands, and both pair
components are strict and evaluated left to right. Subtraction truncates at zero,
and `D0Eif0` requires a boolean condition, regardless of its constructor name.

### Source errors and current boundaries

`SourceEvaluationError` (a `ValueError` subclass) reports an unbound source name,
a reached negative literal or unsupported operator, or a basic misuse such as
projecting a non-pair. There is no static type checker or promise to preserve
arbitrary ill-typed program behavior. A free name in an uncalled source function
body is not looked up until that body executes.

Evaluation follows control flow and does not inspect skipped branches or uncalled
bodies for unsupported forms. Whole-AST rejection, including unused code, belongs
to the compiler milestone. The original source AST is preserved during execution;
the supplied source value records themselves remain the instructor's record types.

## Basic Church values and observation

### High-level purpose

Pure target execution returns functions, rather than built-in integers or
booleans. Encodings let those functions represent data; observers expose readable
answers for comparison with source results. The evaluator itself gains no
knowledge of Church data and has no new arithmetic shortcuts.

`encodings.py` currently supplies these closed pure-target builders:

| Builder | Representation, up to bound-variable names |
| --- | --- |
| `numeral(n)` | `lam s. lam z. s` applied `n` times to `z` |
| `boolean(True)` | `lam t. lam f. t` |
| `boolean(False)` | `lam t. lam f. f` |
| `identity()` | `lam w. w` |

A Church numeral describes repetition. `NUM(2)` is `lam s. lam z. s (s z)`:
take a step function, then a starting value, then apply the step twice. Multiple
arguments use nested single-parameter functions. A Church boolean selects the
first or second supplied argument.

Every builder accepts an optional `names=FreshNameGenerator(...)` so future
compiler/library assembly can share the deterministic naming policy. Without
one, each call starts a fresh generator. Numeral construction uses a Python loop
to build literal syntax, not to execute generated arithmetic. Negative numeral
literals raise `ValueError`; noninteger literals, including booleans, raise
`TypeError`. The boolean builder requires an actual Python boolean literal.

### Observer interface

`observe(value, expected_kind, max_steps=...)` takes a completed closed target
lambda and an explicit `"natural"` or `"boolean"` kind. This annotation is needed
because Church zero and false are alpha-equivalent; the observer does not guess.

An observation constructs pure target applications and calls the **same shared
evaluator** with its own budget. Only after that execution completes does Python
inspect the output shape. It never reduces beneath lambdas or executes generated
arithmetic while inspecting a result.

| `ObservationResult` field | Meaning |
| --- | --- |
| `status` | `"completed"`, `"exhausted"`, or `"malformed"` |
| `value` | Decoded Python integer/boolean on success; `None` otherwise |
| `term` | Final observation output, or unfinished observation term |
| `steps`, `budget` | Observation beta steps and its supplied limit, separate from program execution |
| `diagnostic` | Explanation for exhaustion/malformed output; `None` on success |

An unknown kind or a non-lambda input is an API error. Budget validation and
closed-input rejection follow the target evaluator's documented errors. Malformed
output means the context completed but produced an unrecognized shape; exhaustion
means it still needed evaluation. Neither exposes a successful decoded value.

### Natural-number context and shape

The context from Assignment 6 evaluates `value STEP BASE`:

```text
STEP = lam tail. lam c. lam z. c tail
BASE = lam c. lam z. z
NODE(tail) = lam c. lam z. c tail
```

For two, reduction builds `NODE(NODE(BASE))`. Python walks that finite spine and
counts nodes. It checks each node's local binders rather than requiring fixed
names; a node's selector and zero binders must differ so the selector occurrence
really refers to the outer binder. BASE may reuse its binder name, because its
body refers to the inner binder. Unexpected heads, tails, or base shapes are
rejected. This is structural inspection of the completed data, not normalization.

### Boolean context and markers

The boolean context evaluates `value TRUE_MARKER FALSE_MARKER`. The true marker
is `I = lam w. w`; the false marker is `FALSE = lam t. lam f. f`. Both are closed
values and are not alpha-equivalent. The observer matches the selected marker
up to bound-variable renaming.

These shape checks are not a universal validity test for arbitrary untyped
functions. An unusual function producing an accepted spine or marker can decode
successfully. This limitation is allowed by the assignment.

### Execution and observation example

From `assigns/06/`, in `python -B`:

```python
from MySolution.encodings import boolean, numeral
from MySolution.evaluator import evaluate
from MySolution.observers import observe

execution = evaluate(numeral(2), max_steps=0)
observation = observe(execution.value, "natural", max_steps=4)
print(execution.status, execution.steps)
print(observation.status, observation.value, observation.steps)
print(observe(boolean(False), "boolean", max_steps=2).value)
print(observe(numeral(0), "natural", max_steps=2).value)
print(observe(numeral(0), "boolean", max_steps=2).value)
```

Expected output:

```text
completed 0
completed 2 4
False
0
False
```

Literal `NUM(n)` takes `n + 2` observation steps with this context; literal
booleans take two. Computed values can require more because their bodies can
contain redexes. A completed lambda alone is therefore insufficient for decoding
by matching its original syntax. Tests exercise both computed natural and boolean
bodies, successful completion on the exact observation budget, and divergence
during observation. Pair observation is planned for Step 6.

## Architecture

| Component | Module | Responsibility | Status |
| --- | --- | --- | --- |
| Source integration | `source_ast.py` | Load the supplied AST and visitor interface once | Implemented |
| Source helpers | `source_ops.py` | Printing and source name analysis | Planned |
| Target terms and operations | `target.py` | Immutable `Var`, `Lam`, `App`; printing, names, substitution, alpha-equivalence | Implemented |
| Shared evaluator | `evaluator.py` | Execute source and target syntax through one engine | Implemented |
| Church encodings | `encodings.py` | Construct closed pure terms for data and operations | Numerals, booleans, identity implemented; other combinators pending |
| Compiler | `compiler.py` | Translate using `D0ExpVisitor`; never evaluate input | Planned |
| Observers | `observers.py` | Decode expected data kinds through bounded target contexts | Natural/boolean implemented; pairs pending |
| Demonstrations | `demo.py` | Run and report the required end-to-end examples | Planned |
| Tests | `tests/` | Setup, target operations, evaluation, basic encodings, and scalar observation | In progress |

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

## Execution and observation budgets

Target execution uses weak, left-to-right call-by-value reduction and counts
only beta-value steps. Scalar observation has its own budget and count, with
completion, exhaustion, and malformed outputs distinguished. Pair projections
and recursively observed components will share a separate aggregate observation
budget when implemented in Step 6.

The initial planned demo defaults are 100,000 execution steps and 100,000
observation steps per example. These are not measured requirements or verified
sufficient budgets yet; finalize them after running the terminating examples.
Compilation will support open expressions. Target execution requires closed
terms and reports open inputs clearly.

## Commands and deliverables still pending

The planned demo command is `python -B -m MySolution.demo`. It is **not available
in Step 5**. A later milestone will add its exact options and output details.

`DESIGN.md`, PDF presentation slides, and the 15–20 minute face-visible recording
are pending. Their actual files or recording link will be identified here when
they exist. A parser, web interface, and static type checker are outside the
required implementation.

## Attribution

Source AST classes and the visitor interface come from the instructor-supplied
Assignment 5 `lambda1_vp.py`, used unchanged. Its existing free-variable visitor
is used in setup tests. Its value/environment records and closure representation
are reused in the shared evaluator, and its defining-environment application
approach informs the source cases. Its interpreter is not called: source
evaluation is implemented in the same continuation loop as target execution,
with Assignment 6's operator semantics.

The `FreshNameGenerator` policy and scoped binder-renaming approach in `target.py`
adapt the student's Assignment 5 `MySolution/operations.py`. The target nodes,
operations, and alpha-equivalence checker are implemented separately for this
assignment. No external Church-encoding implementation has been used yet.

The initial Church representations follow Assignment 6 Task 2, and the natural
observation context follows Task 4. The repetition explanation also follows the
local September 3 lecture's Church-numeral slides
(`lectures/lecture-09-03/slides/lambda_calculus_slides.tex`). Boolean observation
uses the distinct closed-marker approach permitted by the assignment.

See [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md) for AI assistance and verification.
