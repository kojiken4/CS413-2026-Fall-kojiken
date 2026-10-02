# Architecture

## Current components (Step 1)

```mermaid
flowchart LR
    Browser --> App[app.py: create_app]
    App --> Controller[controller.py: router]
    Controller --> View[view.py: render_landing_page]
    View --> HTML[templates/index.html]
```

This is the actual dependency graph for the landing page. The model and backend
modules currently declare boundaries only; they do not implement MVC state or
language integration yet. `lambda1.py` is the verbatim supplied language module.

| Responsibility | Implementation | Current status |
| --- | --- | --- |
| Composition | `lambda_web/app.py`, `create_app` | Creates FastAPI and registers routes |
| Controller | `lambda_web/controller.py`, `landing_page` | Handles GET / and requests the view |
| View | `lambda_web/view.py` and `templates/index.html` | Returns static markup without analysis |
| Model | `lambda_web/model.py` | Reserved; source and state rules follow in Step 4 |
| Backend adapter | `lambda_web/backend.py` | Reserved; reader and operations follow in Steps 2-3 |
| Supplied language tools | `lambda_web/lambda1.py` | Copied unchanged; not exposed to requests |

## Chosen direction

The controller will coordinate the model and a replaceable backend. The model
will enforce source/revision, draft, busy, result, and artifact invariants without
HTTP or browser dependencies. The view will forward interactions and render
returned state, without parsing or interpreting source.

1. FastAPI with plain HTML/CSS/JavaScript: explicit HTTP boundaries and test
   backend substitution, at the cost of keeping browser and server state in sync.
2. Controller-coordinated language operations: leaves the model independent of
   language execution, at the cost of orchestration and cleanup in the controller.

## Contract and traces to complete

Later steps will document the implemented Load -> Lint -> Interpret trace,
including undeclared variables, and update the diagram to match real dependencies.
Results will include operation, source revision, outcome, and textual output.
Outcomes will distinguish success, invalid input, language/runtime errors,
backend failures, not implemented, and unavailable.

A future compiler adapter could return generated code with its format and source
revision; the model would invalidate it on source changes or failed recompilation.
Execute would consume that artifact without recompiling. This assignment will
implement neither a compiler nor generated-code execution.
