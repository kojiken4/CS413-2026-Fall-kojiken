# AI Assistance and Review Record

## Tools and scope

OpenAI Codex assisted with assignment interpretation, planning, the objectives
reference, and Step 1 setup. It used local file inspection, patch editing, Git
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

The student has not yet reviewed the Step 1 changes. Automated verification
does not establish student understanding or completion of future requirements.
This record will be updated with later assistance and actual review/testing;
it is not an assertion that unimplemented features work.

## Attribution

The AST and visitor interface are instructor-supplied in
`assigns/05/lambda1_vp.py`. Setup tests use its existing free-variable visitor;
they do not run its interpreter. No Assignment 5 student solution code or
external Church-encoding implementation has been copied in Step 1.
