# Quality Gates

There is one gate per V-model stage (G1–G8). Each gate is a checklist the owning agent self-checks and the orchestrator re-verifies. **Mechanical** items are checked by running a command. **Review** items are checked by the consumer review: the next agent down the left side, plus the paired verifying agent on the right side.

## G1 — Requirements (human approval H1 required)
- [ ] Mechanical: `trace_check --gate requirements` passes
- [ ] The concept (the factory's input) states the problem, target users, and what success looks like, and each goal is numbered `CON-###`. Each CON describes a goal or capability, not an implementation
- [ ] Every actor (human role or external system) is listed and has at least one use case
- [ ] Every interactive CON has at least one use case. Each use case has: primary actor, goal, trigger, preconditions, success and minimal guarantees, a numbered main success scenario, and extensions covering every step that can fail or vary
- [ ] Every system response in every use case flow (main and extensions) is covered by at least one REQ (`Use case step` filled in)
- [ ] Every use case has an SCN for its main success scenario, and one for every extension that ends in failure or a distinct outcome
- [ ] If user stories are enabled: each story follows INVEST, has acceptance criteria, is refined into at least one REQ, and every one of its acceptance criteria is reflected in a REQ's acceptance criteria
- [ ] Mechanical: every REQ Statement is valid **EARS** (`docs/ears.md`), contains exactly one "shall", and matches its declared `EARS` pattern
- [ ] Review: EARS is used well. One consistent system name, conditions placed first (no trailing "when" or "if"), and every failure extension expressed as an `unwanted` (If …, then …) requirement
- [ ] Every requirement is **atomic** (one "shall"), **testable** (has acceptance criteria with concrete values, which become acceptance tests), **unambiguous** (no "fast", "easy", "appropriate", "etc."), and **free of design** (says what, not how)
- [ ] Non-functional requirements are covered for performance, security, privacy, reliability, usability, accessibility, compatibility, and operability, or explicitly marked not applicable with a reason
- [ ] Error and edge behavior is specified (invalid input, limits, empty states, concurrency, failures of dependencies)
- [ ] No contradictions between requirements
- [ ] No blocking open questions
- [ ] Consumer review: Architecture Agent (feasibility) and Acceptance Agent (testability of every acceptance criterion) report no blocking findings

## G2 — Architecture
- [ ] Mechanical: `trace_check --gate architecture` passes
- [ ] Every component has one clear responsibility. No requirement is satisfied by "the whole system" without allocation
- [ ] Every interface defines operations, data formats, errors, and behavior for timeouts, retries, and unavailability
- [ ] Every non-functional requirement has an architectural mechanism (for example a cache for performance, authentication middleware for security)
- [ ] Runtime sequences exist for every use case's main flow, and for extensions that cross component or system boundaries
- [ ] Technology choices recorded as `DEC-###` with alternatives considered
- [ ] `factory/architecture/toolchain.md` defines working commands for build, lint, unit tests with coverage, integration tests, system tests, acceptance tests, and run
- [ ] Consumer review: Design Agent (designability) and System Test Agent (testability of the system as architected) report no blocking findings

## G3 — Design
- [ ] Mechanical: `trace_check --gate design` passes
- [ ] Every `DES` specifies: responsibility, public signatures, inputs and outputs with types and ranges, pre- and postconditions, error handling, state and side effects, and dependencies
- [ ] Algorithms and business rules are explicit enough to derive unit test oracles (boundary values listed)
- [ ] Collaborations are explicit: which units call which, in which order, with which data and error propagation, and how each interface is realized. These are the integration test oracles
- [ ] Design conforms to the interfaces in the architecture (no undeclared cross-component calls)
- [ ] Consumer review: Implementation Agent (implementability), Integration Test Agent (testability of collaborations), and Unit Test Agent (testability of units) report no blocking findings

## G4 — Implementation
- [ ] Mechanical: `trace_check --gate implementation` passes
- [ ] Mechanical: the build succeeds. Lint and type checks are clean (toolchain commands)
- [ ] Mechanical: the complete existing test suite was run; any failures are reported, not hidden
- [ ] No code without an `@implements` tag (or a reviewed `@trace-exempt`)
- [ ] No TODOs, stubs, or placeholder behavior in delivered code
- [ ] No secrets or credentials in source

## G5 — Unit Testing (verifies Implementation)
- [ ] Mechanical: `trace_check --gate unit` passes
- [ ] All UT pass. **100% line and 100% branch coverage** of `src/`. Every exclusion is backed by an accepted `DEC-###`
- [ ] For each implemented unit (`DES`), the cases include nominal, boundary (at, just below, and just above each limit), invalid input, and each error path
- [ ] Unit test report written
- [ ] Recommended: mutation testing score ≥ 80% on core logic, to show the tests actually detect faults

## G6 — Integration Testing (verifies Design)
- [ ] Mechanical: `trace_check --gate integration` passes
- [ ] All IT pass. Every internal interface and every multi-unit component is tested for collaboration as designed: contract conformance, data flow, error propagation, and dependency failure (timeout, unavailable, malformed response)
- [ ] Unit regression green on the same build. Integration test report written

## G7 — System Testing (verifies Architecture)
- [ ] Mechanical: `trace_check --gate system` passes
- [ ] All ST pass on the complete system, built and started from a clean state as `toolchain.md` documents
- [ ] Every component is exercised, every external interface is verified (including failure of external systems), and every scenario runs end to end, including failure, unusual, and edge cases
- [ ] The architecture's non-functional mechanisms are verified at system level (performance under load, security controls, recovery)
- [ ] Integration and unit regression green on the same build. System test report written

## G8 — Acceptance (verifies Requirements; human sign-off H2 required)
- [ ] Mechanical: `trace_check --gate acceptance` passes; `factory/trace/matrix.md` regenerated
- [ ] All AT pass. Every acceptance criterion of every `REQ` (functional and non-functional) is covered by an acceptance test run through the product's public entry points
- [ ] Every `CON` and every `REQ` has a verdict with evidence (test IDs, report references)
- [ ] Every `waived` verdict has an explicit human decision recorded
- [ ] No open defects of severity `critical` or `major`
- [ ] Full regression (all four levels) passes on the same build
- [ ] Known limitations and residual risks are listed
- [ ] The product was run from a clean checkout using the documented toolchain commands
