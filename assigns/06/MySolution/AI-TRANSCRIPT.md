# AI Assistance and Review Record

## Tools and scope

OpenAI Codex assisted with assignment interpretation, planning, the objectives
reference, setup, target operations, and shared source/target evaluation. It used local
file inspection, patch editing, Git status/diff inspection, and Python's
standard-library unittest runner. Compilation, encodings, and observers remain
pending.

## Important requests and decisions

1. **Assignment review:** Explain the assignment clearly and compare another
   chat's summary with the actual specification. The assignment requires one
   shared evaluator and real pure-lambda computation, not precomputed answers.
2. **Implementation plan:** Divide work into independently reviewable,
   committable milestones. Explain unfamiliar concepts concisely, suggest a
   commit message after each step, and pause before continuing. The student
   selected a pause after every milestone; no automatic commits were authorized.
3. **Objectives reference:** Save the component overview for later review.
4. **Step 1:** Set up the package, unchanged source-AST integration, setup tests,
   README, this record, and a requirement-to-evidence checklist.
5. **Step 2:** Add immutable pure target terms, exact printing, name analysis,
   deterministic fresh names, substitution, alpha-equivalence, tests, and updated
   documentation. Stop after verification for the next review checkpoint.
6. **Step 3:** Add bounded weak call-by-value target evaluation, precise step
   counts, completion/exhaustion results, tests, and updated documentation. Keep
   the engine ready for source cases in the next milestone and pause afterward.
7. **Step 4:** Proceed to source evaluation and, from now on, also explain each
   milestone's overarching purpose and how it contributes to the whole assignment.
   Keep the established explain/implement/verify/commit-message/review workflow.

Codex proposed loading the supplied Assignment 5 module by its exact relative
location under a distinct module name. This avoids changing the search path or
accidentally importing another lecture/assignment's `lambda1_vp.py`. The adapter
exposes the original classes rather than copying or redefining them.

The supplied module also defines an interpreter. Those definitions are loaded,
but its evaluator is not called. Its subtraction and boolean support do not
match the required Assignment 6 semantics, so it will not replace the planned
shared evaluator.

## Verification and review status

Step 1 tests exercise the supplied AST, original module location, real visitor
dispatch, source input preservation, and resistance to an unrelated module with
the same ordinary name. All **4 setup tests passed** on Python 3.14.7 using:

```text
python -B -m unittest discover -s MySolution/tests -t . -v
```

The command ran from `assigns/06/`. The README's constructed-AST example produced
its documented output. The supplied file's SHA-256 hash was identical before
and after the changes. Git whitespace and ignore checks also passed.

The student subsequently requested Step 2. This does not establish line-by-line
review of Step 1. Automated verification does not establish student understanding
or completion of future requirements.
This record will be updated with later assistance and actual review/testing;
it is not an assertion that unimplemented features work.

## Attribution

The AST and visitor interface are instructor-supplied in
`assigns/05/lambda1_vp.py`. Setup tests use its existing free-variable visitor;
they do not run its interpreter. No Assignment 5 student solution code or
external Church-encoding implementation was copied in Step 1.

## Step 2 decisions and verification

Codex implemented `target.py` with frozen `Var`, `Lam`, and `App` dataclasses and
the `Term` union. It added exact-format printing, free/all-name analysis,
deterministic fresh names, capture-avoiding substitution, and alpha-equivalence.
The naming policy and scoped-renaming approach adapt the student's Assignment 5
`MySolution/operations.py`; that earlier module is not a runtime dependency.

The explanation distinguished exact structural equality from alpha-equivalence,
and all names from free names. It emphasized that substitution does not evaluate
the replacement and that immutable nodes may safely be shared between results.
Future Church encodings and evaluation were not introduced in this milestone.

All **27 tests passed** on Python 3.14.7 using the same README command: 4 setup
tests and 23 target-operation tests, with additional subcases. These cover open
capture hazards, repeated binders, collisions with names in both input terms,
input preservation, deterministic output, printer formats, identifier rules,
and binding-sensitive alpha-equivalence. The student subsequently requested
Step 3; no additional claim of line-by-line review is made.

## Step 3 decisions and verification

Codex added `evaluator.py` with an iterative evaluation loop and explicit
continuation frames for waiting arguments and waiting function values. Only
beta-value contractions consume the configured budget. Target application calls
the existing capture-avoiding substitution; it never calls a compiler, source
interpreter, or encoded arithmetic shortcut. Source cases will extend the same
engine in Step 4.

The explanation introduced weak evaluation and continuation frames using the
budget-by-budget example `(I I) (I I)`. Completion on the final permitted step is
successful. Exhaustion returns the whole residual term with surrounding
applications reconstructed, and exposes no completed `value`. Closed-execution
restrictions and errors for invalid budgets are documented in README.

All **46 tests passed** on Python 3.14.7 with the README unittest command,
including 19 new evaluator tests. Tests cover both frame contexts, resumption,
precise budgets, strictness, unchanged lambda bodies, determinism, input
preservation, open-term rejection, and 5,000 bounded divergent contractions
without recursive evaluator calls. The student subsequently requested Step 4;
no additional claim of line-by-line review is made.

## Step 4 decisions and verification

The high-level explanation identified source execution as the baseline against
which future compiled results will be compared, alongside explicit expected
answers. It distinguished native source arithmetic from target beta reduction.
The teaching example showed why a function defined with x = 3 must keep that
binding even if called under x = 99.

Codex extended the existing evaluator loop rather than writing another source
evaluator. Both ASTs share application/variable dispatch, continuation sequencing,
and value delivery. Source-only frames handle operators, conditionals, lets, and
pairs. Saved environments prevent a child expression's bindings from leaking
into its siblings. Target application still calls capture-avoiding substitution.

Source values and lexical environments reuse the supplied D0V/ENV record classes,
and the closure-application approach adapts the supplied defining-environment
rules. No supplied interpreter entry point or evaluation visitor is called.
Recursive application adds the function binding before its parameter so the
parameter shadows a coincident function name. Source-specific arithmetic uses
Assignment 6 rules, including subtraction truncated at zero and short-circuit
booleans. These helpers are never called by valid target execution.

The same result structure now exposes completed source values, with steps and
budget set to None. Source evaluation is unbounded and rejects a supplied
non-None budget. Whole-AST validation of unsupported code is deferred to the
compiler; evaluation visits only computations selected by control flow.

All **84 tests passed** on Python 3.14.7: the previous 46 plus 38 source and
engine-boundary tests. Tests cover all source forms/operators, lexical scope,
recursive closures, coincident binders, factorial, Fibonacci, skipped divergence,
strict evaluation via finite error probes, input preservation, independent calls,
and a terminating 2,000-call countdown. Test doubles verify no delegation to the
supplied interpreter, no source calls to target substitution, and no target calls
to source arithmetic. No directly diverging source evaluation was run. Step 4
student review is pending.
