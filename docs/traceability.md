# Traceability

Traceability means every element can be followed from the concept down to code and tests, and back up again. In this factory, **links are written once, in the downstream item, pointing upstream**. The checker derives the reverse direction, so the two directions can never disagree.

## ID scheme

| Prefix | Item | Defined in | Upstream link field | Allowed targets |
|---|---|---|---|---|
| `CON` | Concept goal (the factory's input; checked with the requirements gate) | `factory/concept/` | — | — |
| `UC` | Use case (actor goal with main and alternate flows) | `factory/requirements/` | `Source` | `CON` |
| `US` | User story (optional) | `factory/requirements/` | `Source` | `CON`, `UC` |
| `REQ` | Requirement (functional or non-functional) | `factory/requirements/` | `Source` | `CON`, `UC`, `US` |
| `SCN` | Concrete scenario: one path through a use case | `factory/requirements/` | `Covers` | `REQ` (required), `UC` |
| `EXT` | External actor or system | `factory/architecture/` | — | — |
| `ARCH` | Architecture component | `factory/architecture/` | `Satisfies` | `REQ` |
| `IF` | Interface between components or externals | `factory/architecture/` | `Between` (required), `Satisfies` (optional) | `ARCH`, `EXT` / `REQ` |
| `DES` | Design unit (module, class, function group) | `factory/design/` | `Refines`; optional `Dependencies` | `Refines`: `ARCH`, `IF` (at least one `ARCH`); `Dependencies`: live `DES`, `IF` |
| `UT` | Unit test case (Unit Testing ↔ Implementation) | `factory/verification/unit/` | `Verifies` | `DES` (the implemented unit) |
| `IT` | Integration test case (Integration Testing ↔ Design) | `factory/verification/integration/` | `Verifies` | `DES`, `IF` |
| `ST` | System test case (System Testing ↔ Architecture) | `factory/verification/system/` | `Verifies` | `ARCH`, `IF`, `SCN` |
| `AT` | Acceptance test case (Acceptance ↔ Requirements) | `factory/acceptance/` | `Verifies` | `REQ` |

Acceptance **verdicts** are not items. They are rows in the verdict table of `factory/acceptance/acceptance-report.md`, one per `CON` and `REQ`:

```markdown
| Item | Verdict | Evidence | Notes |
|---|---|---|---|
| CON-001 | accepted | AT-001, AT-002 | |
| REQ-001 | accepted | AT-001, ST-004 | AC1 ✓ AC2 ✓ |
| REQ-009 | waived | — | Q-012: human deferred to next increment |
```

These IDs are not part of the trace graph and the checker ignores them: `Q` (question), `DEC` (decision), `DEF` (defect), `CR` (change request).

### How the levels of the V link up

```
Requirements (CON → UC/US → REQ, SCN)   ◄── verified by ──  Acceptance (AT verifies REQ; verdict per CON/REQ)
Architecture (ARCH, IF, EXT)            ◄── verified by ──  System Testing (ST verifies ARCH, IF, SCN)
Design (DES)                            ◄── verified by ──  Integration Testing (IT verifies DES, IF)
Implementation (code @implements DES)   ◄── verified by ──  Unit Testing (UT verifies each implemented DES)
```

Scenarios are written at the requirements level but run at the system level: each `SCN` is one concrete path through a use case, and system tests run it end to end through the complete system as architected.

### How the requirements-level items relate

Arrows point downstream ("is refined into" / "is verified by"). The links themselves are written in the downstream item.

```
CON ─► UC ─► US (optional) ─► REQ
 │      │                      ▲
 │      └──────────────────────┤   functional REQs from use case steps
 └─────────────────────────────┘   non-functional REQs and constraints

UC + REQ ─► SCN (one concrete path through a use case) ─► ST (system test)
REQ ─► AT (acceptance test of each acceptance criterion)
```

- A **use case** describes how an actor achieves a goal with the system: the main success flow plus its alternate and exception flows. It explains *why* requirements exist and gives them context.
- A **user story** (optional) is a short statement of user value ("As a … I want … so that …"). It is useful for planning and communication. Stories are never binding on their own.
- **Requirements** are the binding, testable "shall" statements. Functional requirements usually come from use case steps or stories (`Source: UC-###` and/or `US-###`). Non-functional requirements and constraints usually come straight from a concept goal (`Source: CON-###`).
- A **scenario** is one concrete path through a use case, with specific data (the main success flow, or one extension). It covers the use case and the requirements it exercises, and system tests verify it.

IDs are `PREFIX-NNN` (three or more digits), unique across the repo, and **never reused**. Before parallel dispatch, the orchestrator scans existing and retired IDs, advances state high-water counters, and persists disjoint ID ranges per work order (including DEC IDs). Agents use only reserved ranges; exhaustion returns partial. Reservations survive interruptions and unused numbers are not recycled. A retired item keeps its ID, marked `(retired)` in its heading, until downstream links have been removed.

## Syntax

### Markdown items

An item is a heading of level 2–4 that starts with the ID. Link fields are list lines inside that item's section, up to the next heading of the same or higher level.

```markdown
### REQ-007: Reject expired sessions
- **Source:** UC-002
- **Type:** functional
- **Priority:** must
- **EARS:** unwanted
- **Statement:** If a request carries a session token older than 30 minutes, then the system shall reject it with error AUTH_EXPIRED.
- **Acceptance criteria:**
  1. A token aged 30:00 is accepted; a token aged 30:01 is rejected.
  2. The rejection response contains code AUTH_EXPIRED and no user data.
```

Link fields accept comma-separated IDs, with or without bold: `- **Satisfies:** REQ-001, REQ-004` or `- Satisfies: REQ-001`.

### Code

Put a comment containing `@implements DES-###` (one or more IDs) next to the module, class, or function that implements the design unit:

```python
# @implements DES-012
def is_session_expired(issued_at: datetime, now: datetime) -> bool:
```

Every non-empty source file under `src/` must contain at least one `@implements` tag. A file that legitimately has no design unit (generated code, framework glue) declares `@trace-exempt <reason>`, and the orchestrator reviews these exemptions.

### Tests

Each automated test carries `@test <ID>`, pointing to its test case in the matching specification:

```python
# @test UT-031
def test_token_at_exact_limit_is_not_expired():
```

The test *case* (in `factory/verification/<level>/` or `factory/acceptance/`) declares what it verifies. The test *code* only points to its case. UT tags must live under `tests/unit/`, IT tags under `tests/integration/`, ST tags under `tests/system/`, and AT tags under `tests/acceptance/`.

## What the checker enforces (cumulative by gate)

`python3 scripts/trace_check.py --gate <stage>`

| Gate | Checks added at this gate |
|---|---|
| `requirements` | At least one `CON` exists. No duplicate IDs. All links resolve to defined IDs of an allowed type. Every `CON` leads to at least one `REQ` (directly or through `UC`/`US`). Every `UC` has a `Source`, is refined into at least one `REQ` (directly or through `US`), and is covered by at least one `SCN`. Every `US` has a `Source` and at least one `REQ`. Every `REQ` has a `Source` and a `Statement` in valid EARS syntax with exactly one "shall", matching its declared `EARS` pattern ([`ears.md`](ears.md)). Every `SCN` covers at least one `REQ` |
| `architecture` | Every `REQ` is satisfied by at least one `ARCH`/`IF`. Every `ARCH` has `Satisfies`. Every `IF` has `Between` with at least one `ARCH` |
| `design` | Every `ARCH` is refined by at least one `DES`. Every `DES` refines at least one `ARCH` |
| `implementation` | Every `DES` is implemented by code. Every `@implements` tag resolves. No untagged source files |
| `unit` | Every `DES` (implemented unit) has a `UT` |
| `integration` | Every internal `IF` (between two components) has an `IT`. Every component with two or more `DES` has an `IT` verifying one of its units or interfaces |
| `system` | Every `ARCH` is exercised by an `ST`. Every external `IF` (involving an `EXT`) and every `SCN` has an `ST` |
| `acceptance` | Every `REQ` has an `AT`. Every `CON` and `REQ` has a verdict row that is `accepted` or `waived`. Accepted CON/REQ verdicts cite live, relevant test IDs in the Evidence cell. Accepted REQs cite an AT directly verifying that REQ. Duplicate verdicts, unrelated/non-test/retired evidence, and unknown cited IDs fail; Notes never supply evidence |

At every test level: each test case has a `Verifies` link and an automated test (`@test`), and every `@test` tag resolves to a live case and lives in the right `tests/<level>/` directory. Comment tags establish traceability; the toolchain and orchestrator must separately prove test discovery and passing execution on the reported build.

Problems found at stages *beyond* the requested gate are reported as warnings, not errors.

Other modes:

- `--impact <ID> [<ID> ...]` follows refinement and declared `Dependencies` to find downstream artifacts and callers. JSON contains `impact` (revision candidates), `regression` (conservative verification candidates including component system tests and related acceptance tests), and `minimum_suite`. Verification propagation does not automatically invalidate upstream specifications. Cross-component dependency impact and direct concept/requirements/architecture/interface changes require slow; public/shared behavior and the accumulation budget may also require slow. A graph suggestion of fast does not refresh higher-level evidence.
- `--matrix PATH` writes the full bidirectional matrix (default `factory/trace/matrix.md` at the `acceptance` gate).
- `--json` produces machine-readable output for automation.
- `--phase specify --gate <unit|integration|system|acceptance>` checks the paired left-side inputs and requested cases, without code, automation, coverage, or verdicts. Other test levels do not block it; no acceptance matrix is generated.
- `--scope ARCH-001 [ARCH-002 ...]` at design, implementation, or unit is an intermediate component check. Only other components' missing coverage obligations become warnings. Duplicates, invalid tags, orphan source, and upstream errors still block. A global gate always uses unscoped execute mode (the default).
- `--baseline <commit> --paths <literal repository-relative paths> --json` compares committed, staged, unstaged, deleted/renamed, and non-ignored untracked files against Git. It is read-only and fails closed for missing refs/paths. Store exact owned paths with every baseline. Trace success alone cannot establish baseline integrity.

## What traceability does not prove

The checker proves that a link *exists*, not that it is *correct*. Whether `UT-031` actually tests the boundary that `DES-012` specifies is a review question. That is why each gate also includes the consumer review and the checklists in [`quality-gates.md`](quality-gates.md).

## Dependency and verification edges

`Refines` defines derivation/ownership. A DES unit's `Dependencies` declares the live DES units or interfaces it uses; self-links, retired dependencies, and invalid target types fail. These edges are used for caller impact, not as substitutes for refinement or verification coverage. Cyclic dependencies terminate safely in impact traversal, although their design remains a review concern.

The checker validates that evidence IDs are relevant to a concept/requirement through the derivation graph; it does not prove that assertions implement the intended oracle, that every acceptance criterion is tested, or that cited tests passed. Waivers still need explicit human decisions, verified by the orchestrator. Record the tested revision, commands, counts, and coverage set in the reports.
