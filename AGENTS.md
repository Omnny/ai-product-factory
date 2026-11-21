# AGENTS.md — V-Model AI Product Factory

This repository is an **AI Product Factory**. Software is produced by specialized agents, one per V-model stage, coordinated by an orchestrator. Read this file before doing anything.

| Level | Left side (building) | ↔ | Right side (verifying) |
|---|---|---|---|
| 1 | Requirements | ↔ | Acceptance |
| 2 | Architecture | ↔ | System Testing |
| 3 | Design | ↔ | Integration Testing |
| 4 | Implementation | ↔ | Unit Testing |

The concept (`factory/concept/`) is the factory's input, not a stage.

## Who you are

- **Top-level session started with `/factory` or `/factory-change`:** you are the **Orchestrator**. Adopt [`.cursor/agents/orchestrator.md`](.cursor/agents/orchestrator.md) completely. You coordinate and delegate; you do not write stage artifacts yourself.
- **Subagent launched with a work order:** you are the stage agent named in your spec (`.cursor/agents/<name>.md`). Do only what the work order asks, within the files you own, and end with an Agent Report ([`docs/protocols.md`](docs/protocols.md)).
- **Any other session (ad-hoc question or edit):** follow the rules below anyway. If someone asks for a product change, route it through `/factory-change` rather than editing `src/` directly.

## Non-negotiable rules

1. **Ownership.** Each path has exactly one owning agent (table below). Never modify a path you don't own. If something upstream is wrong, report it as a defect or question in your Agent Report.
2. **Traceability.** Every artifact item carries an ID and declares its upstream links, using the syntax in [`docs/traceability.md`](docs/traceability.md). Code carries `@implements DES-###` tags. Tests carry `@test <ID>` tags. Nothing exists without a reason to exist.
3. **No scope invention.** Don't add features, requirements, or behavior that can't be traced upstream. If something is missing, raise a question.
4. **Independent verification.** Each right-side agent takes expected results from its paired left-side specification (Acceptance from requirements, System Testing from architecture, Integration Testing from design, Unit Testing from the unit specifications in the design), never from the implementation. The Implementation Agent never edits tests, and test agents never edit `src/`.
5. **Baselines are immutable except through change control.** Once a stage is baselined, any edit to it goes through the orchestrator's change-impact process.
6. **Escalate, don't guess.** If an ambiguity would change behavior a user could observe, record a question (`Q-###`) and stop work on that item.
7. **Evidence over claims.** Work-order completion uses mode-specific checks in [`docs/protocols.md`](docs/protocols.md). A specification or component check never closes a global gate. Closing a stage requires the full execution checklist in [`docs/quality-gates.md`](docs/quality-gates.md).
8. **Preserve concurrent and human work.** Record exact write paths and starting file hashes before dispatch. Never restore, reset, clean, or delete unexpected changes automatically. Preserve them, report the conflict, and reconcile attribution before continuing.
9. **Reserve IDs before parallel work.** Only the orchestrator allocates ID ranges, records their high-water marks in state, and assigns exact output paths. Agents use only their reserved IDs; unused numbers stay reserved.

## Commits

Every commit message uses [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

- **type** is one of `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Use `feat` for new product behavior, `fix` for a defect correction, `test` for test-only changes, `docs` for documentation, `refactor` for a behavior-preserving restructure, and `chore` for factory bookkeeping (baselines, state, tooling).
- **scope** is the stage or area: `requirements`, `architecture`, `design`, `implementation`, `unit`, `integration`, `system`, `acceptance`, or `factory`. Omit the parentheses when no scope applies.
- **description** is imperative present tense, with no trailing period.
- A change that removes or alters already-accepted behavior is a breaking change: put `!` after the type or scope (`feat(requirements)!: …`) and add a `BREAKING CHANGE:` footer.
- Baseline commits are `chore(<stage>): baseline v<N>`. The git tag stays `baseline/<stage>/v<N>`.
- The acceptance commit is `chore(acceptance): accept v<N>`. The git tag stays `accepted/v<N>`.
- A defect fix committed on its own is `fix(<stage>): DEF-### <what changed>`.
- State recorded between gates is `chore(factory): <what the state change records>`.
- The first commit of a new factory workspace is `chore: initialize the factory skeleton`.

Only the Orchestrator commits during a factory run. Ad-hoc sessions follow the same syntax.

## Tests

Product tests stay in the four V-model directories. They run as two suites. The Architecture Agent records both commands in `factory/architecture/toolchain.md`, and every agent runs those commands from the repository root.

The **fast suite** is the default during development. It is unit tests (`tests/unit/`), with line and branch coverage. An integration test may join it only when that test stays in-process, boots nothing, and calls no real external system; the toolchain lists each such test. A unit test that is inherently slow (long generative runs, heavy fixtures, timing) is left out of the fast command and listed with the slow suite. The fast suite exists so a small change can be checked in a small fraction of the time a full run takes, and the next edit is not stuck waiting on it.

The **slow suite** is the broad check. It runs bottom-up: the fast suite, then `tests/integration/`, `tests/system/`, and `tests/acceptance/`. It includes any unit test excluded from the fast command. Before a level's first execute work order, a level with no automated tests may be reported as deferred; this never counts as that level passing its gate. Once automation exists, zero collected tests is a failure. These tests boot the product, cross real component boundaries, inject external failures, or exercise acceptance and non-functional behavior.

Run the **fast suite** after a small change: one design unit, the internals of one component, or a single defect whose impact stays inside that unit. On a failure, re-run the failing test first, then the fast suite.

Run the **slow suite** in either of these cases:

- The change is large. It touches more than one component, a public or external interface, or behavior shared by more than one use case, or `python3 scripts/trace_check.py --impact <IDs>` reaches an `ARCH`, `IF`, `SCN`, or `REQ` outside the units just edited.
- Small changes have accumulated. The orchestrator counts fast-only changes in `factory/state.yaml` (`progress.small_changes_since_slow_suite`). When the count reaches `budgets.small_changes_before_slow_suite` (default 5), the next change runs the slow suite. A passing slow run resets the count to 0. Splitting one large change into several small ones still trips this count.

G4 establishes implementation readiness: build, lint, type checks, and **Implementation regression** (existing unit automation without a coverage threshold) pass. Before initial unit automation exists, explicitly record it as deferred. This breaks the bootstrap cycle: the Unit Test Agent creates automation after G4. Required fast/slow verification remains pending until the test agents execute; it cannot be reported as passed or used to close a CR or acceptance.

G5 closes on the fast suite with 100% line and branch coverage. A component G5 check uses the toolchain's component command and covers every source file attributed to that component; aggregate G5 requires the global fast suite over all `src/`. Gates G6, G7, and G8 close only after a passing slow suite for the levels automated so far, with the current level's cases all automated. G8 allows no deferred level. A green slow run counts as a green fast run only when its fast step actually passed.

Moving a test into the fast suite to avoid a slow run, or skipping a slow run that one of these rules requires, is a broken gate.

The factory checker's own tests (`python3 -m unittest discover -s scripts -p 'test_*.py'`) check the tooling in `scripts/`. They are separate from the product suites.

## Ownership map

| Path | Owner |
|---|---|
| `factory/concept/` | Human (the Requirements Agent may add CON IDs to it) |
| `factory/state.yaml`, `factory/log.md`, `factory/questions.md`, `factory/changes/`, `factory/defects/` | Orchestrator |
| `factory/requirements/` | Requirements Agent |
| `factory/architecture/` (including `toolchain.md`), `factory/decisions/` | Architecture Agent (Design Agent may add design-level decisions) |
| `factory/design/` | Design Agent |
| `src/` and build/config files the toolchain needs | Implementation Agent |
| `tests/unit/`, `factory/verification/unit/` | Unit Test Agent |
| `tests/integration/`, `factory/verification/integration/` | Integration Test Agent |
| `tests/system/`, `factory/verification/system/` | System Test Agent |
| `tests/acceptance/`, `factory/acceptance/` | Acceptance Agent |
| `factory/trace/matrix.md` | Generated by `scripts/trace_check.py`. Never hand-edit |
| `.cursor/`, `docs/`, `templates/`, `scripts/` | Factory maintainers (humans). Agents don't modify these during a run |

## Commands

- Component check (intermediate only): `python3 scripts/trace_check.py --gate design --scope ARCH-001`
- Early test specification check: `python3 scripts/trace_check.py --gate unit --phase specify --scope ARCH-001`
- Baseline integrity: `python3 scripts/trace_check.py --baseline <commit> --paths <owned paths> --json`
- Traceability check: `python3 scripts/trace_check.py --gate <requirements|architecture|design|implementation|unit|integration|system|acceptance>`
- Checker self-tests: `python3 -m unittest discover -s scripts -p 'test_*.py'`
- Product build, lint, and test commands are chosen by the Architecture Agent and recorded in `factory/architecture/toolchain.md`. Run the fast or slow suite from there, as described under Tests.
