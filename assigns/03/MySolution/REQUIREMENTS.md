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

The instructor's brief is the stakeholder input available for this specification. No additional stakeholder answers have been received. The following questions remain unresolved; no working assumptions have yet been adopted to answer them. Any later answer or assumption will be recorded against its question ID, with assumptions explicitly distinguished from stakeholder decisions.

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
