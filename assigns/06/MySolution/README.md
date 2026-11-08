# Assignment 6: Extended LAMBDA to Pure Lambda Calculus

## Overview

The implementation provides the Python package, source-AST adapter, immutable target terms,
printing, name analysis, deterministic fresh names, capture-avoiding substitution,
alpha-equivalence checking, and one shared evaluator for source and target
programs. Church data, arithmetic, comparisons, boolean operations, pairs, and
bounded scalar/nested-pair observation are implemented. Visitor compilation
connects every required source form to target execution and observation, including
delayed conditionals, short-circuit booleans, and recursion through CBV Z. One
command now runs all 14 required demonstrations and saves their pure target
terms.

[REQUIREMENTS.md](../REQUIREMENTS.md) provides the detailed requirement IDs.
[DESIGN.md](DESIGN.md) explains the representations, translation rules,
correctness argument, and tradeoffs in a short report. This README provides
commands, interfaces, worked examples, and measured results.
[AI-TRANSCRIPT.md](AI-TRANSCRIPT.md) records AI assistance and verification.
Further explanation can be found in the [slide deck](presentation/CS413-Midterm-Presentation-fa26.pdf) created for this midterm,
as well as the [video presentation](https://docs.google.com/videos/d/1OOeFozjGlZWAsqtMKme9hC88oLxhoKIlEF5Wg2dz03E/play?usp=sharing) that refers to this slide deck.

## Setup and tests

Use **Python 3.12 or later**. No third-party packages or installation steps are
required. Run these commands from `assigns/06/`:

```powershell
python --version
python -B -m unittest discover -s MySolution/tests -t . -v
python -B -m MySolution.demo
```

`-B` prevents bytecode-cache writes, including beside the supplied Assignment 5
file. The package also ignores local bytecode caches and virtual environments.

Verified on **Python 3.14.7**: all **213 tests pass**, and the default demo command
reports `Summary: 14/14 demonstrations passed.` with all 14 fully expanded terms
saved. Python 3.12 is the required minimum; other interpreter versions have not
been tested in this workspace. Milestone history is recorded in AI-TRANSCRIPT.md.

The adapter requires the repository's existing `assigns/05/lambda1_vp.py` in
its original relative location. It loads that exact file by location without
changing the module search path or modifying the supplied code. All solution
modules access its classes through `MySolution.source_ast.ast`. Run from the
repository checkout: copying MySolution alone omits this required supplied file.

## Main interfaces

| Import/module | Call | Result |
| --- | --- | --- |
| `source_ast` | `ast.D0E...(...)` | Supplied source syntax; constructors are used instead of a parser |
| `source_ops` | `pretty_source(source)` | Readable source syntax |
| `compiler` | `compile_expr(source)` | Pure target term; `CompilationError` for unsupported syntax |
| `evaluator` | `evaluate(source)` | Source value; no target count or finite budget |
| `evaluator` | `evaluate(target, max_steps=N)` | Completed lambda or exhausted residual, with execution count/budget |
| `observers` | `observe(value, kind, max_steps=N)` | Decoded data or exhausted/malformed outcome, with separate count/budget |
| `target` | `pretty(term)`, `free_vars(term)`, `substitute(term, name, replacement)` | Printed syntax, free names, or a new term |

Pass an observer kind of `"natural"`, `"boolean"`, or
`("pair", left_kind, right_kind)`, nesting pair kinds as needed. Observe only a
completed target value. Detailed status fields, errors, and worked examples
appear below.

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
terms can reach Python's recursion limit; these helpers do not implement
stack-independent traversal. Constructor child shapes are assumed
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

### Summary

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
it. Use source evaluation only for terminating examples; divergent examples
are compiled and run with a target budget.

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
the pure target Z encoding now supplies recursion without native target closures.

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

### Source errors and supported inputs

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

### Summary

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

### Summary

The compiler assembles translated programs from these closed operation
builders. They give pure lambda programs arithmetic, comparisons, and structured
data while keeping the evaluator independent of those meanings. The Z builder
additionally supplies recursion, as explained in the compiler section below.

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
both directions of that relation. [DESIGN.md](DESIGN.md) includes the construction
and its invariant in the correctness argument.

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

## Compilation

### Summary and entry point

The compiler connects the components into a pipeline. Instead of
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
| `fix f(x). e` | `Z (lam f. lam x. C[e])` |

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

### Call-by-value recursion

The target has no recursive-definition node. Instead, `z_combinator()` builds
the assignment's closed pure term, with deterministic fresh bound names:

```text
Z = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
C[fix f(x). e] = Z (lam f. lam x. C[e])
```

The function `F = lam f. lam x. C[e]` receives its recursive function as `f`.
Z gives F a delayed recursive call, `lam v. x x v`. This wrapper is already a
value, so call-by-value can pass it to F without immediately unfolding recursion
again. F then returns its argument-taking function. Only applying the wrapper
to an actual argument resumes the recursive computation. The two copies of the
Z arm use separate fresh binders and match the required term up to bound names.

This is called a fixed-point combinator because it supplies a function with a
way to call itself. Under CBV, Z's result behaves like F supplied with a delayed
version of itself. Ordinary Y passes `x x` directly; CBV keeps trying to evaluate
that self-application before F can return a function, even when F ignores recursion.
Tests verify both behaviors with the same evaluator.

Two separate delays matter for factorial: Z postpones the next recursive call
until its argument arrives, while conditional thunks prevent the recursive
branch from running when the base case is selected. Compiling a fix expression
does not execute it. Evaluating its translation takes three beta-value steps
to return a function without entering its body. Calling that function enters
the body. Nested `lam f. lam x` also preserves the source rule that a parameter
shadows the recursive name when both names coincide.

Here is factorial built directly with the supplied source constructors:

```python
from MySolution.compiler import compile_expr
from MySolution.evaluator import evaluate
from MySolution.observers import observe
from MySolution.source_ast import ast

fact = ast.D0Efix("fact", "n", ast.D0Eif0(
    ast.D0Eop2("==", ast.D0Evar("n"), ast.D0Eint(0)),
    ast.D0Eint(1),
    ast.D0Eop2("*", ast.D0Evar("n"), ast.D0Eapp(
        ast.D0Evar("fact"), ast.D0Eop2("-", ast.D0Evar("n"), ast.D0Eint(1)),
    )),
))
program = ast.D0Eapp(fact, ast.D0Eint(4))
execution = evaluate(compile_expr(program), max_steps=100000)
observation = observe(execution.value, "natural", max_steps=100000)
print(evaluate(program).value.arg1, observation.value)
print(execution.steps, observation.steps)
```

Expected output:

```text
24 24
471 333
```

| Program | Source and observed target answer | Execution steps | Observation steps |
| --- | --- | --- | --- |
| Factorial 0 | 1 | 31 | 3 |
| Factorial 4 | 24 | 471 | 333 |
| Fibonacci 0 | 0 | 25 | 2 |
| Fibonacci 1 | 1 | 37 | 3 |
| Fibonacci 5 | 5 | 1794 | 45 |

These counts use the current fully expanded terms and separate budgets of
100,000 for execution and observation. They are measured reduction counts,
not complexity bounds. The demo and recursive/source tests share the factorial,
Fibonacci, and LOOP constructors in `examples.py`; explicit answers independently
check the source and compiled results. These constructors were moved from the
source tests so the executable demonstration never depends on tests.

### Coverage and diagnostics

`CompilationError` is importable from `compiler.py`. Every fix body is checked
for unsupported syntax, including unapplied definitions and skipped branches.

| Requirements | Current evidence |
| --- | --- |
| CMP-01, CMP-08 | Every required constructor/operator, factorial, Fibonacci, and recursive pair results; source and observed target results checked against explicit answers |
| CMP-02 | Visitor translation is compositional; arithmetic, recursive functions, and divergent programs compile with evaluator entry points disabled |
| CMP-03 | Tests traverse output and require only exact Var/Lam/App node types; closed source examples produce closed terms |
| CMP-04, CMP-05 | Let-initializer scope, nested shadowing, recursive lexical scope, coincident fix binders, open forms, and free-variable equality |
| CMP-06 | Deterministic repeated compilation, source snapshots, common encoding names, fresh thunk parameters against free and unused bound names |
| CMP-07 | Negative/unsupported forms rejected in direct input, skipped branches, unapplied functions, short-circuit operands, and fix bodies |
| QLT-01, QLT-02 | Supplied visitor dispatch verified; compiler imports neither evaluator nor observers; shared engine and observers unchanged by recursive compilation |

`tests/test_compiler.py` supplies 29 tests and `tests/test_source_ops.py` supplies
5. `tests/test_recursive_compiler.py` adds 17 tests. Both nonrecursive
self-application and the required fix-based LOOP check skipped computations and
selected/strict computations under target budgets. Recursive tests additionally
cover exact Z structure, Y versus Z, three-step function creation, both Fibonacci
base cases, recursive binding and capture hazards, nested pairs, deterministic
compilation, input preservation, and invalid unused recursive bodies. No directly
diverging source evaluation is run.

## Architecture

| Component | Module | Responsibility | Status |
| --- | --- | --- | --- |
| Source integration | `source_ast.py` | Load the supplied AST and visitor interface once | Implemented |
| Source helpers | `source_ops.py` | Source printing, full syntax validation, all-name collection | Implemented |
| Target terms and operations | `target.py` | Immutable `Var`, `Lam`, `App`; printing, names, substitution, alpha-equivalence | Implemented |
| Shared evaluator | `evaluator.py` | Execute source and target syntax through one engine | Implemented |
| Church encodings | `encodings.py` | Construct closed pure terms for data, operations, and recursion | All required builders implemented, including Z |
| Compiler | `compiler.py` | Translate using `D0ExpVisitor`; never evaluate input | All required source forms implemented |
| Observers | `observers.py` | Decode expected data kinds through bounded target contexts | Natural, boolean, and nested pairs implemented |
| Examples | `examples.py` | Construct all 14 required source ASTs and explicit expected answers | Implemented; shared recursive fixtures |
| Demonstrations | `demo.py` | Run and report the required end-to-end examples; save pure terms | All 14 pass with default budgets |
| Tests | `tests/` | Component, compiler pipeline, and demonstration acceptance tests | All 213 pass |

The runtime pipeline is:

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
explicit expected answers. Divergent examples run only through bounded
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

The measured demo defaults are **10,000 execution steps** and **10,000 observation
steps per example**, independently configurable. These cover all terminating
required examples: the largest execution count is 1,794 (Fibonacci 5), and the
largest observation count is 333 (factorial 4). The standalone factorial
example above retains its explicitly configured 100,000-step budgets. Neither
choice imposes a universal bound on arbitrary programs or their running time.
Compilation supports open expressions. Target execution requires closed
terms and reports open inputs clearly.

## Demonstration command and results

From `assigns/06/`, run:

```powershell
python -B -m MySolution.demo
```

The runner constructs fresh source ASTs, compiles each, evaluates its target
term, and observes completed values using the specified data kind. For each
terminating case it also evaluates the original source with the same shared
engine. PASS requires agreement between source result, observed target result,
and the explicit expected answer, with booleans distinguished from integers.
Expected answers are comparisons, never inputs to target computation.

For each case the report includes the fully printed source, saved pure-term
location, execution status/budget/count, separate observation status/budget/count,
decoded answer when available, expected answer, source answer or skip reason,
and PASS/FAIL. Execution exhaustion skips observation and prints its zero used
steps and configured budget; observation exhaustion or malformed output prints
no decoded answer and fails a case expecting data. Other examples still run.

All fully expanded generated terms are saved as UTF-8 text in
`MySolution/demo-output/DEMO-01.lambda.txt` through `DEMO-14.lambda.txt`. They use
the exact target printer notation and contain no unresolved encoding names.
Paths in the report are absolute. Re-running replaces these named generated
files. The default output folder is ignored by Git and can be regenerated by
the command; it contains demonstration artifacts, not required source code.

Options, runnable from the same directory:

```powershell
python -B -m MySolution.demo --help
python -B -m MySolution.demo --execution-budget 10000 --observation-budget 10000 --output-dir MySolution/demo-output
```

Both budgets accept nonnegative integers, including zero. Relative output paths
are resolved from the working directory; quote paths that contain spaces. Exit
status **0** means all 14 cases matched expectations, **1** means at least one
did not, and **2** reports invalid command arguments or an output-file error.
A smaller execution or observation budget may make a terminating case fail;
this is reported as insufficient resources, never as a decoded answer.

The two curated cases marked for expected exhaustion skip unbounded source
evaluation. The runner is a demonstration collection, not a termination checker
for arbitrary source programs. A PASS for an exhausted case means it used the
budget as expected; finite exhaustion by itself does not prove nontermination.

Measured default-command results on Python 3.14.7:

| ID | Example | Decoded/expected result | Execution steps | Observation steps |
| --- | --- | --- | --- | --- |
| DEMO-01 | `2 + 3 * 4` | 14 | 4 | 26 |
| DEMO-02 | `2 - 5` | 0 | 87 | 2 |
| DEMO-03 | `if 2 <= 3 then 7 else 9` | 7 | 77 | 9 |
| DEMO-04 | `let x = 3 in (lam y. x + y) 4` | 7 | 4 | 13 |
| DEMO-05 | `fst (pair 2 true)` | 2 | 6 | 4 |
| DEMO-06 | `snd (pair 2 true)` | true | 6 | 2 |
| DEMO-07 | `(lam f. f 3) (lam x. x + 1)` | 4 | 4 | 10 |
| DEMO-08 | `if true then 1 else LOOP` | 1 | 3 | 3 |
| DEMO-09 | `(lam x. 0) LOOP` | Expected execution exhaustion | 10000 | 0 (skipped) |
| DEMO-10 | Factorial 4 | 24 | 471 | 333 |
| DEMO-11 | Fibonacci 5 | 5 | 1794 | 45 |
| DEMO-12 | `LOOP` | Expected execution exhaustion | 10000 | 0 (skipped) |
| DEMO-13 | `true and false` | false | 3 | 2 |
| DEMO-14 | `false or true` | true | 3 | 2 |

The final line is `Summary: 14/14 demonstrations passed.` All 12 terminating
results agree with source evaluation. Counts are implementation measurements,
not grading requirements. IDs/order follow REQUIREMENTS.md Section 7.1; the
original Assign06 table lists the same programs in a different order.

`tests/test_demo.py` verifies every case's source shape, expected data/kind,
closed pure output, source preservation, source/target agreement, and both
looping cases without unbounded source evaluation. It also runs the real command
in a fresh process and compares all 14 saved terms with compiler output. Failure
checks cover exhausted budgets, exact completion boundaries, malformed
observations, false/integer confusion, invalid arguments, output-file errors,
and continuing the collection after failed expectations. Temporary test folders
stay inside the solution and are removed after each test.

## Limitations

- Compilation and substitution support open terms; target execution rejects
  them with `OpenTermError`. The correctness claim covers closed, well-typed
  source programs returning natural, boolean, or finite data-pair results.
- There is no static type checker. Required unsupported syntax is rejected
  throughout the source AST, but arbitrary malformed ASTs and ill-typed programs
  are outside the supported input contract.
- Target step budgets count contractions, not elapsed time, tree size, or memory.
  The execution loop is iterative, but printing, compilation, name analysis,
  substitution, and nested-pair observation contain recursive traversals that
  can reach Python's recursion limit. Substitution may duplicate large terms.
- Observation requires a caller-supplied kind and does not recognize every
  invalid untyped encoding. It reports malformed outputs and budget exhaustion;
  a partial computation is never a successfully decoded result.
- Source evaluation is unbounded. The demo's explicitly marked looping examples
  skip it. The runner is a fixed collection, not a general termination checker.
- Signed integers, division, a source parser, and a web interface are not
  implemented. Required source arithmetic uses naturals and truncated subtraction.

## Submission Documents and Links

| Deliverable | Location/status |
| --- | --- |
| Source and automated tests | Python modules and `tests/` in this directory |
| Setup, demo command, interfaces, results, limitations, attribution | This README |
| Design report, all translation rules, predecessor, correctness, tradeoffs | [DESIGN.md](DESIGN.md) |
| AI assistance, important requests, verification record | [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md) |
| PDF presentation slides | [Link to presentation](presentation/CS413-Midterm-Presentation-fa26.pdf) |
| Presentation recording discussing program design | [Public link to video](https://docs.google.com/videos/d/1OOeFozjGlZWAsqtMKme9hC88oLxhoKIlEF5Wg2dz03E/play?usp=sharing) |

The final submission excludes virtual environments, installed dependencies,
caches, and temporary test folders. Demo term files can be regenerated.
The video embedded within the submission files may not have audio. If this is the case,
try instead viewing the video presentation via the [public link provided](https://docs.google.com/videos/d/1OOeFozjGlZWAsqtMKme9hC88oLxhoKIlEF5Wg2dz03E/play?usp=sharing). Note that you must be signed into an email
under BU's domain to be able to view this video online.

## Attribution

Source AST classes and the visitor interface come from the instructor-supplied
Assignment 5 [lambda1_vp.py](../../05/lambda1_vp.py), used unchanged. Its existing free-variable visitor
is used in setup tests. Its value/environment records and closure representation
are reused in the shared evaluator, and its defining-environment application
approach informs the source cases. Its interpreter is not called: source
evaluation is implemented in the same continuation loop as target execution,
with Assignment 6's operator semantics.

The `FreshNameGenerator` policy and scoped binder-renaming approach in `target.py`
adapt the student's Assignment 5 [operations.py](../../05/MySolution/operations.py). The target nodes,
operations, and alpha-equivalence checker are implemented separately for this
assignment. No external Church-encoding implementation was used.

The source printer and all-name traversal in `source_ops.py` adapt the student's
Assignment 5 [operations.py](../../05/MySolution/operations.py), with Assignment 6-specific validation
added. The compiler's visitor dispatch follows the supplied interface and the
local [October 6 visitor slides](../../../lectures/lecture-10-06/slides/lambda1_vp.tex). Translation and delayed-branch rules follow
Assignment 6 Task 3, using the existing encoding builders.

The initial Church representations follow Assignment 6 Task 2, and the natural
observation context follows Task 4. The repetition explanation also follows the
local September 3 lecture's Church-numeral slides
([September 3 slide source](../../../lectures/lecture-09-03/slides/lambda_calculus_slides.tex)). Boolean observation
uses the distinct closed-marker approach permitted by the assignment.

The pair-state predecessor and derived operation definitions are constructed
from the assignment's Church numerals, booleans, and required pair representation.
They are explained above and tested through reduction; no external encoding
implementation was copied. The Z builder and fix translation follow the exact
rules supplied in Assignment 6 Tasks 2 and 3, using fresh bound names.

See [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md) for AI assistance and verification.
