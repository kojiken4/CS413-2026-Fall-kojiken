# Assignment 3: AI Assistance Record

**Tool:** OpenAI Codex desktop app using GPT-6 Astra and GPT-6 Luna (manually selected contingent on prompt difficulty)

**Status:** First draft. This document summarizes the important prompts, assistance, and review in the assignment conversation; it is not a verbatim transcript. Prompt descriptions below are paraphrases unless quoted.

## Use of AI

I used Codex to explain the assignment and lecture material, plan the work, and draft REQUIREMENTS.md incrementally. The source material was Assign03.md, LAMBDA-UI-informal-requirements.md, and the supplied requirements engineering slide deck. The assignment instructions and stakeholder brief governed the specification; the slide deck provided an example of the method.

## Important Prompts and Assistance

| Request | Significant assistance |
| --- | --- |
| Review Assign03.md and explain what it requires. | Codex summarized the five tasks, the required submission files, and the distinction between specifying the environment and implementing software. |
| Review the requirements engineering slide deck before starting the assignment. | Codex explained elicitation, clarification, functional and quality requirements, user and system requirements, and acceptance scenarios using the deck's office-hours example. Its fictional agreements were not treated as LAMBDA stakeholder answers. |
| Plan the assignment tasks sequentially with incremental commit checkpoints. | Codex proposed a sequence covering stakeholders and scope, questions and assumptions, requirements, acceptance criteria, traceability, and review. |
| Create a draft of step one, explain where responses belong, and do not commit. | Codex initially drafted the purpose, stakeholders, boundary, and scope. It explained that the submission instructions permit the task responses in REQUIREMENTS.md and that unanswered stakeholder questions may remain unresolved or use labeled assumptions. |
| Continue through the requirements, interfaces, and acceptance criteria, drafting edits before requiring my manual review. | Codex drafted 19 functional requirements, five quality requirements, interface dependencies, and eight acceptance scenarios. It proposed explicit saving, test-comparison rules, retained submitted versions, cancellation behavior, and a response-time target, labeling them as assumptions or proposals. |
| Explain traceability and proceed with the specification review. | Codex mapped all 24 requirements to the brief or explicit proposals and recorded three review issues with corresponding document corrections. |

## Manual Review

After each step, I manually reviewed the content and made changes as needed. I carefully validated each step and the changes intended for each commit before staging them, ensuring that the contents added were within the scope of the current task being completed. I handled staging and committing myself, and then assigned the commit titles for each increment. I edited system requirements as needed, changing the wording to better reflect the contents of the brief.

## Checks and Corrections Performed by Codex

Codex checked the draft against the assignment and brief, verified that all 24 functional and quality requirements had traceability entries, checked that requirement references resolved, and ran a formatting check. During the final review step, it clarified optional features in the scope, connected question statuses to provisional assumptions, and revised the starter-example scenario. These corrections are recorded in Section 11 of REQUIREMENTS.md.
