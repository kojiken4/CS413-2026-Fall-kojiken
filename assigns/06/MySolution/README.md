# Assignment 6: Extended LAMBDA to Pure Lambda Calculus

## Current status

Steps 1–7 provide the Python package, source-AST adapter, immutable target terms,
printing, name analysis, deterministic fresh names, capture-avoiding substitution,
alpha-equivalence checking, and one shared evaluator for source and target
programs. Church data, arithmetic, comparisons, boolean operations, pairs, and
bounded scalar/nested-pair observation are implemented. Nonrecursive visitor
compilation now connects source ASTs to target execution and observation, including
delayed conditionals and short-circuit booleans. Z, fix compilation, and the demo
remain pending. Passing these tests does not establish a proof of correctness.

The assignment is authoritative: [Assign06.md](../Assign06.md).
[REQUIREMENTS.md](../REQUIREMENTS.md) provides the detailed requirement IDs.

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

Step 6 verification on Python 3.14.7: all **147 tests passed**, adding 21 encoded
operation tests and 14 pair-observation tests. All previous tests still pass.

Step 7 verification on Python 3.14.7: all **181 tests passed**, adding 29 compiler
tests and 5 source-helper tests. Existing suites remain unchanged.

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
is the supplied dataclass representation. `pretty_source` now prints source
syntax for demonstrations; `target.pretty` prints the generated target syntax.

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
  restriction applies only to execution; the compiler supports open expressions too.

## Source evaluation

### High-level purpose

Source execution establishes a baseline for checking the compiler. Run an
original program with the shared engine, then run and observe its compiled target
term. Both results must agree with the explicit expected answer.
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
bodies for unsupported forms. The compiler checks the whole AST, including unused
code, before translating it. The original source AST is preserved during execution;
the supplied source value records themselves remain the instructor's record types.

## Basic Church values and observation

### High-level purpose

Pure target execution returns functions, rather than built-in integers or
booleans. Encodings let those functions represent data; observers expose readable
answers for comparison with source results. The evaluator itself gains no
knowledge of Church data and has no new arithmetic shortcuts.

`encodings.py` supplies these basic closed pure-target builders:

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
lambda and an explicit `"natural"`, `"boolean"`, or recursive
`("pair", left_kind, right_kind)` description. These are Python metadata, not
additional target AST forms. The annotation is needed because Church zero and
false are alpha-equivalent; the observer does not guess.

An observation constructs pure target applications and calls the **same shared
evaluator** with its own budget. Only after that execution completes does Python
inspect the output shape. It never reduces beneath lambdas or executes generated
arithmetic while inspecting a result.

| `ObservationResult` field | Meaning |
| --- | --- |
| `status` | `"completed"`, `"exhausted"`, or `"malformed"` |
| `value` | Decoded Python integer/boolean or recursively nested tuple on success; `None` otherwise |
| `term` | Scalar output on scalar success; original pair value on pair success; failing context output/residual on failure |
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
during observation. Pair observation extends this mechanism as described below.

## Encoded operations and pairs

### High-level purpose

The compiler assembles translated programs from these closed operation
builders. They give pure lambda programs arithmetic, comparisons, and structured
data while keeping the evaluator independent of those meanings. Recursive
translation remains for Step 8.

All operation builders accept the same optional `names=` generator. The following
notation abbreviates expanded pure ASTs; each multi-parameter expression is
implemented with nested single-parameter lambdas.

| Builder | Encoded rule or behavior |
| --- | --- |
| `pair()` | `PAIR a b p = p a b` |
| `first()`, `second()` | `FST p = p TRUE`; `SND p = p FALSE` |
| `successor()` | `SUCC n s z = s (n s z)` |
| `predecessor()` | Iterate a pair of previous/current counts; select previous |
| `is_zero()` | `ISZERO n = n (lam ignored. FALSE) TRUE` |
| `add()` | `ADD m n s z = m s (n s z)` |
| `subtract()` | `SUB m n = n PRED m` |
| `multiply()` | `MUL m n s z = m (n s) z` |
| `negation()` | `NOT p = p FALSE TRUE` |
| `conjunction()`, `disjunction()` | `AND p q = p q FALSE`; `OR p q = p TRUE q` |
| `less_equal()` | `LE m n = ISZERO (SUB m n)` |
| `less_than()` | `LT m n = NOT (LE n m)` |
| `greater_equal()`, `greater_than()` | Reverse the operands of LE/LT |
| `equal()` | `EQ m n = AND (LE m n) (LE n m)` |
| `not_equal()` | `NE m n = NOT (EQ m n)` |

Addition performs n steps and then m more steps. Multiplication repeats a group
of n steps m times. These repetitions are encoded applications reduced by the
engine, not Python arithmetic on decoded operands.

The library AND/OR combinators take evaluated boolean arguments under ordinary
call-by-value. Passing a divergent expression as an argument still exhausts the
execution budget. The compiler preserves source short-circuiting by delaying
computations with thunks; it does not apply these builders directly to an
unwrapped right-hand source computation.

### Predecessor construction

Start with `PAIR 0 0` and repeat this pure update n times:

```text
UPDATE state = PAIR (SND state) (SUCC (SND state))
PRED n = FST (n UPDATE (PAIR 0 0))
```

| Updates | State (previous, current) |
| --- | --- |
| 0 | (0, 0) |
| 1 | (0, 1) |
| 2 | (1, 2) |
| 3 | (2, 3) |

After n updates, current represents n and previous represents `max(n - 1, 0)`.
Selecting previous therefore gives predecessor; zero performs no updates and
still returns zero. Repeating predecessor implements truncated subtraction.
Consequently `m <= n` holds exactly when `SUB m n` is zero. Equality requires
both directions of that relation. This explanation will also inform DESIGN.md.

### Pair observation and aggregate budget

A Church pair accepts a selector, which receives both components. FST supplies
TRUE to select the first; SND supplies FALSE to select the second. Pair construction
evaluates both components left to right before the resulting pair lambda is a value.

The caller first evaluates the pair program to a lambda. Observation then runs
the first projection and observes its result, followed by the second projection
and its result, recursively. Every context receives only the remaining portion
of the original observation budget. Components do not get fresh budgets.

For a pair of literal 2 and true, the current builders use these observation steps:

| Context | Steps |
| --- | --- |
| First projection | 4 |
| Observe natural 2 | 4 |
| Second projection | 4 |
| Observe boolean true | 2 |
| Total observation | 14 |

A failing component reports a path such as `result.second` or
`result.first.projection`. No partially decoded tuple is returned, even when
earlier components succeeded. Successful pair observation returns the original
pair lambda in `.term`, since multiple contexts have run and there is no single
aggregate observation-output term. Scalar success and failure retain the output
semantics in the interface table above.

### Encoded computation example

From `assigns/06/`, in `python -B`:

```python
from MySolution.encodings import add, boolean, multiply, numeral, pair
from MySolution.evaluator import evaluate
from MySolution.observers import observe
from MySolution.target import App

product = App(App(multiply(), numeral(3)), numeral(4))
program = App(App(add(), numeral(2)), product)
execution = evaluate(program, max_steps=100)
answer = observe(execution.value, "natural", max_steps=1000)
print(answer.status, answer.value)

inner_pair = App(App(pair(), numeral(2)), boolean(True))
nested_pair = App(App(pair(), inner_pair), numeral(3))
execution = evaluate(nested_pair, max_steps=4)
answer = observe(
    execution.value, ("pair", ("pair", "natural", "boolean"), "natural"), max_steps=27
)
print(execution.steps, answer.value, answer.steps)
```

Expected output:

```text
completed 14
4 ((2, True), 3) 27
```

## Nonrecursive compilation

### High-level purpose and entry point

This milestone connects the existing pieces into a compiler pipeline. Instead of
manually assembling target applications, pass a source AST to
`compile_expr(source_expression)` and obtain a pure target term. Compilation
does not calculate source answers, invoke an evaluator, or mutate its input.

`compiler.py` uses the supplied `D0ExpVisitor` interface. Each source node's
`accept` method dispatches to the matching compiler visitor method, which
translates its children and combines their results. That is compositional
translation: a program's output is assembled from its subprograms' translations.
There are no retained source primitives or unresolved library abbreviations.

### Full syntax checks and deterministic naming

Before translation, `source_ops.validate_source` visits every source node,
rejecting negative literals, unsupported operator spellings, and invalid
identifiers. It returns all variable and binder names, including unused binders.
It inspects both conditional branches and all function bodies without executing
them. Therefore unsupported code fails compilation even when it would not run.

The compiler seeds a new `FreshNameGenerator` with that complete name set and
shares it across every encoding builder and introduced thunk binder. Source
binders retain their names; generated binders avoid all original names and all
previous generated names. Repeated calls produce the same target AST regardless
of earlier compilations. Open terms compile and preserve their free-variable sets;
execution remains restricted to closed target terms.

`source_ops.pretty_source` renders syntax for inspection, including unsupported
forms for diagnostics. Printing and validation are separate read-only visitors.

### Thunks and forcing

A thunk is a function wrapping a computation to delay it. Since a lambda is a
value under weak call-by-value, creating `lam u. C[branch]` does not execute the
branch. The fresh parameter u is deliberately unused.

The compiler expands this helper notation into ordinary target terms:

```text
D(c, t, f) = (c (lam u. t) (lam v. f)) I
I = lam w. w
```

The Church boolean c selects one branch lambda. Applying that selected lambda to
the closed dummy value I forces its body; the other lambda body stays untouched.
Only evaluation is delayed: both branches were checked and translated during
compilation. This preserves target call-by-value application rather than changing
the evaluator's strategy.

### Implemented translation rules

`C[e]` means the translation of e. Capitalized encodings and D are explanatory
abbreviations that are fully expanded into Var/Lam/App nodes in actual output.

| Source | Target rule |
| --- | --- |
| Natural n | `NUM(n)` |
| Boolean b | `TRUE` or `FALSE` |
| Variable x | `x` |
| `lam x. e` | `lam x. C[e]` |
| `e1 e2` | `C[e1] C[e2]` |
| `let x = init in body` | `(lam x. C[body]) C[init]` |
| `not e` | `NOT C[e]` |
| Numeric `e1 op e2` | `OP C[e1] C[e2]`, with the corresponding arithmetic/comparison builder |
| `if c then t else f` | `D(C[c], C[t], C[f])` |
| `e1 and e2` | `D(C[e1], C[e2], FALSE)` |
| `e1 or e2` | `D(C[e1], TRUE, C[e2])` |
| `pair e1 e2` | `PAIR C[e1] C[e2]` |
| `fst e`, `snd e` | `FST C[e]`, `SND C[e]` |

The let initializer is outside its name's binding, as required. Application,
arithmetic, and pair construction retain left-to-right strictness through their
target application structure. Generated thunk parameters are fresh and unused,
so they cannot capture a source free variable. Valid unused branches remain in
the output, preserving `FV(C[e]) = FV(e)` even for constant conditions.

### Pipeline example

From `assigns/06/`, in `python -B`:

```python
from MySolution.compiler import compile_expr
from MySolution.evaluator import evaluate
from MySolution.observers import observe
from MySolution.source_ast import ast
from MySolution.source_ops import pretty_source

source = ast.D0Elet("x", ast.D0Eint(3), ast.D0Eapp(
    ast.D0Elam("y", ast.D0Eop2("+", ast.D0Evar("x"), ast.D0Evar("y"))), ast.D0Eint(4)
))
target = compile_expr(source)
execution = evaluate(target, max_steps=100)
observation = observe(execution.value, "natural", max_steps=1000)
print(pretty_source(source))
print(evaluate(source).value.arg1, observation.value)
```

Expected output:

```text
(let x = 3 in ((lam y. (x + y)) 4))
7 7
```

### Coverage and interim boundary

`CompilationError` is importable from `compiler.py`. In Step 7, any source fix
expression raises an explicit error that recursive translation is added in Step 8,
including an unused fix expression. Validation still inspects fix bodies first,
so unsupported literals/operators there are diagnosed. This intermediate boundary
does not satisfy the final assignment's recursion requirement yet.

| Requirements | Current evidence |
| --- | --- |
| CMP-01, CMP-08 | Every nonrecursive constructor/operator; source and observed target results checked against explicit answers; fix translation pending |
| CMP-02 | Visitor translation is compositional; arithmetic and nonrecursive self-application compile with evaluator entry points disabled |
| CMP-03 | Tests traverse output and require only exact Var/Lam/App node types; closed source examples produce closed terms |
| CMP-04, CMP-05 | Let-initializer scope, nested shadowing, lexical functions, open forms, and free-variable equality; fix binding tests pending |
| CMP-06 | Deterministic repeated compilation, source snapshots, common encoding names, fresh thunk parameters against free and unused bound names |
| CMP-07 | Negative/unsupported forms rejected in direct input, skipped branches, unapplied functions, short-circuit operands, and fix bodies |
| QLT-01, QLT-02 | Supplied visitor dispatch verified; compiler imports neither evaluator nor observers; existing engine/encoding/observer modules unchanged |

`tests/test_compiler.py` supplies 29 tests and `tests/test_source_ops.py` supplies
5. Before fix translation is available, divergence stress tests use nonrecursive
self-application built from lambdas and applications. They check both skipped
computations and selected/strict computations under target budgets. The required
fix-based LOOP, factorial, and Fibonacci compilation tests remain for Step 8.
No directly diverging source evaluation is run.

## Architecture

| Component | Module | Responsibility | Status |
| --- | --- | --- | --- |
| Source integration | `source_ast.py` | Load the supplied AST and visitor interface once | Implemented |
| Source helpers | `source_ops.py` | Source printing, full syntax validation, all-name collection | Implemented |
| Target terms and operations | `target.py` | Immutable `Var`, `Lam`, `App`; printing, names, substitution, alpha-equivalence | Implemented |
| Shared evaluator | `evaluator.py` | Execute source and target syntax through one engine | Implemented |
| Church encodings | `encodings.py` | Construct closed pure terms for data and operations | All required data/operations implemented; Z pending |
| Compiler | `compiler.py` | Translate using `D0ExpVisitor`; never evaluate input | Nonrecursive forms implemented; fix pending |
| Observers | `observers.py` | Decode expected data kinds through bounded target contexts | Natural, boolean, and nested pairs implemented |
| Demonstrations | `demo.py` | Run and report the required end-to-end examples | Planned |
| Tests | `tests/` | Existing component tests plus source helpers and nonrecursive compiler pipeline | In progress |

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

The compiler depends on source/target syntax, validation helpers, and encoding
builders. It imports neither evaluator nor observers. The evaluator does not
import or invoke the compiler. Observers build pure target contexts and use the
same evaluator.

## Execution and observation budgets

Target execution uses weak, left-to-right call-by-value reduction and counts
only beta-value steps. Scalar observation has its own budget and count, with
completion, exhaustion, and malformed outputs distinguished. Pair projections
and recursively observed components share one aggregate observation budget,
separate from program execution.

The initial planned demo defaults are 100,000 execution steps and 100,000
observation steps per example. These are not measured requirements or verified
sufficient budgets yet; finalize them after running the terminating examples.
Compilation supports open expressions. Target execution requires closed
terms and reports open inputs clearly.

## Commands and deliverables still pending

The planned demo command is `python -B -m MySolution.demo`. It is **not available
in Step 7**. A later milestone will add its exact options and output details.

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

The source printer and all-name traversal in `source_ops.py` adapt the student's
Assignment 5 `MySolution/operations.py`, with Assignment 6-specific validation
added. The compiler's visitor dispatch follows the supplied interface and the
local October 6 visitor slides. Translation and delayed-branch rules follow
Assignment 6 Task 3, using the existing encoding builders.

The initial Church representations follow Assignment 6 Task 2, and the natural
observation context follows Task 4. The repetition explanation also follows the
local September 3 lecture's Church-numeral slides
(`lectures/lecture-09-03/slides/lambda_calculus_slides.tex`). Boolean observation
uses the distinct closed-marker approach permitted by the assignment.

The pair-state predecessor and derived operation definitions are constructed
from the assignment's Church numerals, booleans, and required pair representation.
They are explained above and tested through reduction; no external encoding
implementation was copied. The required Z builder remains for Step 8.

See [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md) for AI assistance and verification.
