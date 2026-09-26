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
