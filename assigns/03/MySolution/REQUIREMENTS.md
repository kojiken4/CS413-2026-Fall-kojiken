# LAMBDA Testing Environment Requirements Specification

## 1. Purpose

This document defines the requirements for a local web-based environment for writing and testing LAMBDA programs. The environment will let students and the instructor enter programs, submit them to the LAMBDA compiler tools, inspect results, and save examples as tests that can be run again after compiler changes.

The goal is to support student practice and classroom demonstrations through reliable editing, clear results, and repeatable tests. These requirements are based on the instructor's brief and will guide development and evaluation of the environment.

## 2. Stakeholders and Goals

Students and the instructor are the primary users of the environment. The compiler interface provider is an external stakeholder whose tools the environment depends on. The roles below may overlap; a student working on the compiler may also use the environment to write programs.

| Stakeholder | Role and main goals |
| --- | --- |
| Students writing LAMBDA programs | Write or load programs, modify examples, compile or run them, understand results and errors, and save work for later use. The environment must also support students who have not used the compiler before. |
| Students modifying the compiler | Maintain named tests with expected outcomes and rerun test collections to identify failures introduced by compiler changes. |
| Course instructor | Demonstrate and modify examples during lectures, inspect available compiler information, and retain examples for future use. The instructor also provides the needs that guide the system's scope and priorities. |
| Compiler interface provider | Coordinate the interface between the LAMBDA tools and the environment, including the supported operations and information available in compiler responses. |

## 3. System Boundary

The environment provides the browser interface for editing and loading programs, managing examples and test collections, submitting compilation or execution requests, and displaying the returned results. It is also responsible for preserving user work and comparing test outcomes with their expected results.

The LAMBDA tools are an external dependency responsible for processing and executing programs and returning results or diagnostics. The environment presents the information these tools provide, including source locations and intermediate representations when available. Developing the compiler itself is a separate project.

The environment team must coordinate with the compiler interface provider to establish how requests and responses are exchanged. The brief does not identify that provider or define the interface. Since the current interpreter uses abstract syntax trees constructed in Python and source notation remains undecided, the environment cannot assume that the tools already accept typed LAMBDA source text. These details remain subject to clarification.

## 4. First-Version Scope

The first version will run locally on a student's or instructor's computer and be accessed through a browser. Its scope prioritizes reliable editing, understandable results, and repeatable tests, as requested in the brief.

| Area | Included capabilities |
| --- | --- |
| Programs and examples | Enter, paste, and load programs; modify starter examples while retaining access to the originals; and save work for later use. |
| Compilation and execution | Request compilation without execution or run a program, display results, and inspect compiler information such as ASTs or generated code when available. |
| Errors and ongoing work | Distinguish compilation errors, runtime failures, and compiler unavailability; show source locations when supplied; preserve work during compiler outages; support stopping long-running work; and associate results with the submitted program version. |
| Test collections | Maintain named tests with expected values or expected compilation rejection, rerun collections, and show summaries and individual outcomes. One troublesome test must not prevent use of the remaining collection. Saved examples and collections must remain available across refreshes and sessions. |
| Usability and setup | Provide local setup instructions, keyboard access to main tasks, messages that do not depend only on color, and a usable interface while compilation or execution is in progress. |
| Integration development | Allow demonstrations using clearly labeled sample compiler responses while the tools are unfinished, with eventual connection to the real tools through the agreed interface. |

The accepted program representation, compiler interface, saving behavior, cancellation support, supported browsers, and measurable quality targets remain subject to clarification. Inclusion in this scope does not establish that the compiler already supports every requested operation.

Public hosting, user accounts, and simultaneous collaborative editing are outside the first version, as stated in the brief. Compiler development remains outside the environment project.

Collection sharing is proposed for a later version because the instructor explicitly permits its deferral. Sophisticated visual effects and additional features of a full development environment are also proposed for deferral so that the first version can focus on the stated priorities. These deferrals are scope proposals, not additional stakeholder agreements.

## 5. Clarification Questions and Assumptions

The instructor's brief is the stakeholder input available for this specification. No additional stakeholder answers have been received. The questions below remain open for stakeholder clarification. Where a working assumption supports the draft requirements, it is recorded separately and does not represent a stakeholder decision.

| ID | Clarification question | Why the answer matters | Status |
| --- | --- | --- | --- |
| Q-01 | Who will provide the compiler interface, and what operations and response information will it support, including results, errors, source locations, and intermediate representations? | Identifies the integration contact and establishes what the environment can request and display without requiring it to implement compiler functionality. | Unresolved |
| Q-02 | What program representation should users enter or load in the first version, given that source notation is undecided and the current interpreter accepts Python-constructed ASTs? | Determines the accepted editor and file input and what can be submitted to the language tools. | Unresolved |
| Q-03 | Should programs and test collections be saved automatically or through an explicit save action, and must unfinished edits also survive refreshes and later sessions? | Defines when work is considered saved and exactly what must be restored, rather than assuming that preserving saved programs also preserves every edit. | Unresolved |
| Q-04 | Which expected value types must tests support, and should an expected compilation failure match any rejection or a particular diagnostic? | Defines how the environment determines whether a test passed and prevents unrelated failures from being counted as the expected outcome. | Unresolved |
| Q-05 | What cancellation support will the tools provide, and should a nonterminating test be stopped automatically after an agreed limit or require user intervention? | Determines how execution can actually be stopped and how the remaining tests can continue. Any time limit would need to be agreed or explicitly proposed. | Unresolved |
| Q-06 | When a result arrives after the program has been edited, should users be able to inspect the submitted version, or is a clear indication that the result belongs to an earlier version sufficient? | Establishes how users identify the program that produced a result without assuming a full version-history feature. | Unresolved |
| Q-07 | Which browsers and operating systems must the first version support, and what local setup prerequisites are acceptable? | Defines the supported environment and the conditions under which setup instructions and compatibility will be evaluated. | Unresolved |
| Q-08 | What task-completion and interface-response targets should define acceptable usability and responsiveness, and under what program sizes and test-collection sizes should they be assessed? | Makes terms such as "straightforward" and "promptly" verifiable while separating ordinary interface response from compiler execution time. | Unresolved |

### Working assumptions

The following proposals allow specific behavior to be described while stakeholder answers are unavailable.

| ID | Related question | Proposed assumption and reason |
| --- | --- | --- |
| A-01 | Q-03 | Provide explicit saving of programs and test collections, with saved content available after refresh or reopening in the same browser profile on the same computer. This defines a minimum persistence guarantee. Recovery of unsaved edits and access from other browsers remain unresolved. |
| A-02 | Q-04 | Initially compare integer and Boolean results by both type and value. An expected compilation rejection matches any compiler-reported compilation error, but never a runtime or environment failure. This supports the test examples in the brief without assuming diagnostic-specific matching. |
| A-03 | Q-06 | Retain the submitted program with its result so users can inspect it after editing the current program. This identifies the input that produced a result without requiring a complete edit history. |
| A-04 | Q-05 | Use user-requested cancellation in the first version; no automatic execution time limit is proposed at this stage. Actual termination requires confirmation from the language tools, whose cancellation support remains unresolved. This distinguishes requesting cancellation from successfully stopping execution. |

## 6. Functional Requirements

Each requirement describes observable system behavior. "Shall" indicates required behavior when the feature is included. Essential requirements support the core editing, execution, and testing workflow. Optional requirements support teaching or early demonstrations and may be deferred without removing the core workflow. These priorities are proposed from the brief's stated goals.

Requirements involving the language tools depend on the interface and input representation identified in Q-01 and Q-02. They specify the needed behavior without assuming that the current interpreter already provides it.

| ID | Priority | Requirement |
| --- | --- | --- |
| FR-01 | Essential | The environment shall allow users to enter, paste, and edit program content. The accepted representation remains subject to Q-02. |
| FR-02 | Essential | The environment shall allow users to load a program from a local file into the editor. Supported program files remain subject to Q-02. |
| FR-03 | Essential | The environment shall provide selectable starter examples and allow users to modify a selected example while retaining access to its original content. |
| FR-04 | Essential | The environment shall allow users to save a program and select a saved program for further editing or execution. Saving follows A-01. |
| FR-05 | Essential | The environment shall restore saved programs and test collections after a page refresh or a later session under the conditions in A-01. |
| FR-06 | Essential | On a compile-only request, the environment shall submit the current program for compilation and display success or compilation diagnostics without requesting execution. |
| FR-07 | Essential | On a run request, the environment shall submit the current program for execution through the language tools and display the returned result or failure. |
| FR-08 | Essential | The environment shall distinguish compilation errors, runtime failures, and environment failures using text labels and display the available explanation for each failure. |
| FR-09 | Essential | When a diagnostic includes a source location, the environment shall identify that location in the submitted program associated with the diagnostic. |
| FR-10 | Optional | When the compiler supplies an AST or generated code, the environment shall allow users to open and close a view of that information without requiring them to inspect it to run a program. |
| FR-11 | Essential | If the compiler cannot be reached, the environment shall report compiler unavailability, preserve the current editor content and saved work, and allow a new request after connectivity is restored. |
| FR-12 | Essential | The environment shall provide a stop action for an active execution. It shall distinguish a pending cancellation request, confirmed termination, and cancellation failure or unavailability, and shall report execution as stopped only after termination is confirmed, as proposed in A-04. |
| FR-13 | Essential | The environment shall associate each result with the program submitted for that request and allow inspection of that program. If the editor content has changed, the environment shall indicate that the result belongs to an earlier version, as proposed in A-03. |
| FR-14 | Essential | The environment shall allow users to create and edit named tests containing a program and an expected outcome: an integer value, a Boolean value, or compilation rejection, as proposed in A-02. |
| FR-15 | Essential | The environment shall allow users to save and reopen collections of named tests, preserving each test's name, program, and expected outcome under A-01. |
| FR-16 | Essential | The environment shall mark a completed test as passed only when its actual outcome matches the expected outcome under A-02. Other completed outcomes shall be marked failed; cancellation or environment failure shall be reported separately and shall not count as a pass. |
| FR-17 | Essential | The environment shall allow users to run a saved test collection. A failed test or a test whose cancellation is confirmed shall not prevent the remaining tests from running. If the compiler becomes unavailable, the environment shall identify tests that could not run and retain the collection for another attempt. |
| FR-18 | Essential | For a collection run, the environment shall display each test's status and summary counts for the displayed statuses. Users shall be able to inspect each test's expected outcome and actual result, diagnostic, or reason it did not complete. |
| FR-19 | Optional | If a demonstration using sample compiler responses is provided, the environment shall visibly label the mode and its displayed results as simulated. Simulated results shall not be presented as actual compiler execution. |
