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
