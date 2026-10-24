# AI Assistance and Review Record

## Tools and scope

OpenAI Codex assisted with assignment interpretation, planning, the objectives
reference, Step 1 setup, and Step 2 target operations. It used local file inspection, patch editing, Git
status/diff inspection, and Python's standard-library unittest runner. No
compiler, evaluator, encodings, or observers have been implemented yet.

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
and binding-sensitive alpha-equivalence. Step 2 student review is pending.
