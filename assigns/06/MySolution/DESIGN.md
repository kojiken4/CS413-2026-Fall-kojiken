# Design: Extended LAMBDA to Pure Lambda Calculus

## Purpose and architecture

This compiler preserves the behavior of the assignment's extended language while
removing its built-in data and operations. The target contains exactly immutable
`Var`, `Lam`, and `App` nodes. Numerals, booleans, pairs, operations, and recursion
are expanded functions, never evaluator primitives.

`source_ast.py` loads the unchanged Assignment 5 AST and visitor interface by
file location. `source_ops.py` validates and prints source syntax. `compiler.py`
dispatches through `D0ExpVisitor`, recursively compiles children, and assembles
their translations using `encodings.py`. Neither compilation nor encoding
construction invokes evaluation. Validation examines unused branches and function
bodies, rejecting negative literals, division, unsupported operators, and invalid
identifiers. It does not perform type inference.

`evaluator.py` provides one execution loop for both languages. `observers.py`
reads target data through that same loop. `examples.py` supplies source ASTs;
`demo.py` coordinates compilation, execution, observation, and comparison with
source results and explicit expectations.

## Representations and predecessor

A Church numeral represents repeated application: two applies a supplied step
twice to a starting value. Booleans choose between two arguments. A pair passes
its components to a selector; TRUE selects the first and FALSE the second.
Uppercase names below abbreviate expanded terms. Multiple parameters and
arguments mean nested single-parameter abstractions and left-associated applications.

```text
NUM(n)  = lam s. lam z. s^n z
TRUE    = lam t. lam f. t
FALSE   = lam t. lam f. f
PAIR    = lam a. lam b. lam p. p a b
FST     = lam p. p TRUE
SND     = lam p. p FALSE
SUCC    = lam n. lam s. lam z. s (n s z)
UPDATE  = lam p. PAIR (SND p) (SUCC (SND p))
PRED    = lam n. FST (n UPDATE (PAIR NUM(0) NUM(0)))
ISZERO  = lam n. n (lam ignored. FALSE) TRUE
ADD     = lam m. lam n. lam s. lam z. m s (n s z)
SUB     = lam m. lam n. n PRED m
MUL     = lam m. lam n. lam s. lam z. m (n s) z
NOT     = lam p. p FALSE TRUE
AND     = lam p. lam q. p q FALSE
OR      = lam p. lam q. p TRUE q
LE      = lam m. lam n. ISZERO (SUB m n)
LT      = lam m. lam n. NOT (LE n m)
GE      = lam m. lam n. LE n m
GT      = lam m. lam n. LT n m
EQ      = lam m. lam n. AND (LE m n) (LE n m)
NE      = lam m. lam n. NOT (EQ m n)
```

Predecessor carries both the previous and current number. Starting at `(0, 0)`,
UPDATE produces `(0, 1)`, `(1, 2)`, then `(2, 3)`. After k updates the state is
`(max(k-1, 0), k)`. Applying a Church numeral n to UPDATE performs n updates;
FST therefore returns the predecessor. Zero performs no updates and returns zero.
SUB repeats this operation, naturally truncating subtraction at zero. Testing
that subtraction yields zero gives less-than-or-equal; the remaining comparisons
follow by argument reversal, negation, and conjunction.

Each builder returns a closed pure term. Python loops may construct a literal's
syntax, but generated arithmetic executes solely through target reduction.
Library AND/OR accept already evaluated values; source short-circuiting requires
the delayed compilation rules below.

## Translation and delayed control flow

Let C[e] denote compilation. OP maps each supported arithmetic/comparison spelling
to its corresponding builder above. Fresh u and v do not occur in their branches.
The supplied source constructor `D0Eif0` uses a boolean condition despite its name.

```text
I = lam w. w
D(c, t, f) = (c (lam u. t) (lam v. f)) I
Z = lam g. (lam x. g (lam v. x x v)) (lam x. g (lam v. x x v))
```

| Source | Translation |
| --- | --- |
| Natural n, boolean b | `NUM(n)`, `TRUE` or `FALSE` |
| Variable x | `x` |
| `lam x. e` | `lam x. C[e]` |
| `e1 e2` | `C[e1] C[e2]` |
| `e1 op e2`, for `+ - * < <= > >= == !=` | `OP C[e1] C[e2]` |
| `not e` | `NOT C[e]` |
| `if c then t else f` | `D(C[c], C[t], C[f])` |
| `a and b` | `D(C[a], C[b], FALSE)` |
| `a or b` | `D(C[a], TRUE, C[b])` |
| `let x = init in body` | `(lam x. C[body]) C[init]` |
| `pair a b` | `PAIR C[a] C[b]` |
| `fst e`, `snd e` | `FST C[e]`, `SND C[e]` |
| `fix f(x). e` | `Z (lam f. lam x. C[e])` |

A thunk is a function wrapping a delayed computation. Creating either branch
lambda does not execute its body. The condition selects one thunk; application
to the dummy value I forces that branch. Directly supplying branch computations
to a Church boolean would evaluate both arguments under call-by-value, incorrectly
running an unused LOOP. Both branches are still validated and compiled.

For recursion, `lam f. lam x. C[e]` receives the recursive function as f. Z supplies
the wrapper `lam v. x x v`, which is already a value. It postpones another
unfolding until an argument arrives. Ordinary Y supplies self-application directly
and unfolds prematurely under call-by-value. Evaluating a compiled fix takes three
beta-value steps to return a function without executing its body. Conditional
thunks separately prevent the recursive branch from running at a base case.

## Names and scope

Before translation, validation collects every source variable and binder,
including unused binders. One fresh-name generator reserves that set and all
names it generates. Candidates follow `base_counter`; a single counter advances
on every attempt, including collisions, across all bases. A new generator per
compilation makes output deterministic regardless of previous compilations.

Source binders keep their names. Generated encodings and thunk parameters cannot
capture source variables. The let binder surrounds only its body, excluding its
initializer. Fix becomes nested function-name and parameter binders, so coincident
names give the parameter precedence. Compilation preserves open expressions'
free-variable sets, although execution requires closed terms. Substitution uses
its own fresh-name pool and preserves its inputs; frozen target nodes permit safe
subtree reuse.

## Evaluation and observation interfaces

`compile_expr(source)` returns a target term or raises `CompilationError`.
`evaluate(target, max_steps=N)` uses weak, left-to-right call-by-value: function,
argument, then substitution. It never reduces beneath lambdas or performs eta
reduction. One iterative continuation loop records pending work for both languages.
Source execution uses lexical closures and defining environments; source arithmetic
uses Python operations only on source values. Target execution uses substitution
and cannot invoke source arithmetic.

Evaluation reports `completed` or `exhausted`, the resulting/residual term, steps,
and budget. A lambda completes with zero steps, including at budget zero. A value
reached on the last permitted contraction completes successfully. Counts include
only beta-value contractions; exhaustion is not proof of nontermination. Source
calls omit the budget and have no target step count. Known looping examples
never enter unbounded source evaluation.

`observe(value, kind, max_steps=N)` has a separate budget and returns `completed`,
`exhausted`, or `malformed`, with decoded data or a diagnostic. A completed lambda
may contain pending computation, so matching its initial syntax cannot decode
arithmetic reliably. The caller must supply the kind: Church zero and FALSE
share a representation.

```text
STEP = lam tail. lam c. lam z. c tail
BASE = lam c. lam z. z
Natural context: value STEP BASE
Boolean context: value I FALSE
```

Natural observation builds BASE or nested `lam c. lam z. c tail` nodes; Python
counts this finite spine, respecting bound names. Boolean observation recognizes
the selected distinct closed marker up to alpha-equivalence. Pair observation
evaluates projections and observes components recursively, left before right,
sharing one aggregate observation budget. Failures discard partial decoded pairs.
These inspections never execute target arithmetic in Python.

## Correctness argument, evidence, and tradeoffs

The intended claim is: for closed, well-typed programs in the specified source
language that terminate with natural, boolean, or finite data-pair results,
observing their compiled results yields the same data, given sufficient execution,
observation, and host resources. Functions are related by application behavior,
not by identical syntax or step counts.

The argument follows compositional translation. Literals denote the stated
encodings; operations implement their data meanings. Application retains the
source's function-before-argument evaluation and demands the argument even if
unused. Let uses this same strict application rule while preserving initializer
scope. Pairs evaluate both components before projection. Conditionals force only
the selected branch; and/or force the right operand only when required. Z's
delayed self-reference supplies recursive calls while preserving lexical scope.
Fresh generated names and capture-avoiding substitution preserve bindings.
The observers then expose the corresponding data through pure contexts.

All 213 tests pass; all 14 demonstrations match expectations. Tests cover
capture hazards, shadowing, exact budgets, every operator, recursive examples,
nested pairs, skipped divergence, strict divergence, unsupported unused code,
pure output, immutable inputs, and compilation with evaluation disabled. Factorial
4 yields 24 using 471 execution and 333 observation steps; Fibonacci 5 yields 5
using 1794 and 45. Demo budgets are independently 10,000 each. Finite tests cannot
establish the claim universally; no formal proof is supplied.

Named immutable trees make output inspectable and scope tests direct, but
substitution can duplicate terms. Fully expanded encodings and repeated pair
projections favor transparent construction over speed. Recursive structural
traversals can hit Python's recursion limit; step budgets bound contractions,
not memory or elapsed time. Open execution, a parser, static typing, signed
integers, and universal recognition of invalid untyped encodings are outside
scope. Results are verified on Python 3.14.7; the required minimum is 3.12.

## Attribution

Representations, Z, translation rules, and observation contexts follow
[Assign06.md](../Assign06.md), with obligations tracked in
[REQUIREMENTS.md](../REQUIREMENTS.md). Source classes, visitor, and value/environment
records come from the unchanged [Assignment 5 module](../../05/lambda1_vp.py).
Naming, scoped renaming, and source-printing traversal adapt the student's
[Assignment 5 operations](../../05/MySolution/operations.py). Predecessor and
derived operations are constructed from the assignment's representations; no
external encoding implementation was copied. [AI-TRANSCRIPT.md](AI-TRANSCRIPT.md)
records Codex assistance and verification. [README.md](README.md) provides commands,
measured results, and the remaining presentation deliverables.
