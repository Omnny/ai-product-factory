# Protocols

Agents communicate only through the orchestrator. They use two message types: the **Work Order**, sent from the orchestrator to an agent, and the **Agent Report**, sent back from the agent to the orchestrator. Defects, questions, change requests, and decisions are kept as persistent records in files created from the templates in `templates/`.

## Work Order (orchestrator → agent)

The orchestrator sends the work order as the full prompt when it launches a stage or support subagent. A subagent starts with **no conversation history**. The work order must therefore contain all the context it needs, including relevant persistent-memory excerpts and their primary sources. These excerpts must respect the receiving agent's information rules.

```markdown
# Work Order WO-<n>: <short title>

- **Agent:** <requirements-agent | architecture-agent | design-agent | implementation-agent |
             unit-test-agent | integration-test-agent | system-test-agent | acceptance-agent | memory-agent>
- **Mode:** <author | revise | review | specify | execute | fix>
- **Trigger:** <initial run | CR-### | DEF-### | consumer review of <stage>>

## Objective
<one or two sentences: what must be true when this work order is done>

## Scope
- In scope IDs: <e.g., ARCH-002, IF-003, or "all REQ">
- Out of scope: <explicitly excluded items>

## Inputs (read these; all are baselined unless noted)
- <path> — <why it matters>

## Context
<decisions, answers to questions, relevant memory lessons and primary references, defect details, prior attempts and why they failed; include only sources this agent may read>

## Constraints
- Write only to: <exact reserved files, including reports/config; no overlapping files>
- Reserved IDs: <prefix: inclusive range; request another range in the report if exhausted; none for memory support work>
- Starting snapshot: <state active-work-order record; hashes/index/untracked inventory>
- Check phase and scope: <specify|execute; component ARCH IDs or global; not applicable to memory support work>
- Commands / coverage source set: <exact toolchain commands and component files>
- Pending verification: <required checks deferred until initial automation exists, or none>
- Iteration budget: <n>
- <anything else: e.g., "do not change public interface IF-003">

## Expected outputs
- <files / IDs to create or update>

## Exit criteria
- <mode-specific checklist below + applicable quality-gate criteria; memory uses its support completion criteria>
- For stage work: `python3 scripts/trace_check.py --gate <stage> [--phase specify] [--scope ARCH-###]` passes
- <unscoped execution is mandatory when closing an aggregate gate; no V-model gate applies to memory work>
```

## Agent Report (agent → orchestrator)

Every agent ends its turn with exactly this structure, as its final message:

```markdown
# Agent Report — WO-<n>

- **Agent:** <name>
- **Status:** <done | partial | blocked | failed>
- **Summary:** <2–4 sentences: what was achieved>

## Artifacts changed
- <path> — <created|updated|retired> — IDs: <list>

## Gate self-check
| Criterion | Result | Evidence |
|---|---|---|
| <criterion> | pass/fail | <command output summary, counts, file refs> |

## Questions (blocking work on an item)
- Q-draft: <question> — Affects: <IDs> — Options: <A (recommended) / B / C> — Impact if unanswered: <...>

## Defects found (in artifacts this agent does not own)
- DEF-draft: <title> — Class: <code|test|design|architecture|requirement|environment> — Against: <IDs/paths> — Evidence: <failing test, quote of spec, output>

## Assumptions made (non-blocking)
- <assumption> — Affects: <IDs> — Reversible: yes/no

## Suggested next steps
- <what the orchestrator should schedule next>
```

When the orchestrator records `Q-draft` and `DEF-draft` entries, it assigns their actual numbers. This keeps agents from competing for the next ID.

## Modes

| Mode | Meaning |
|---|---|
| `author` | Create the stage artifact from upstream inputs, or the initial memory summary for memory support work |
| `revise` | Update specific IDs because of a CR, defect, or review finding, or reconcile pending memory events from their sources |
| `review` | Consumer review of an upstream artifact, or memory recall and reconciliation. Read-only; findings come back as defects or questions |
| `specify` | (Right-side agents: Unit Test, Integration Test, System Test, Acceptance) Write test case specifications from the paired left-side artifact |
| `execute` | (Right-side agents) Implement automated tests for the specified cases, run them, and report results. The Acceptance Agent also records verdicts |
| `fix` | Fix a routed defect in the agent's own artifact |

## Records

| Record | Template | Location | Created by |
|---|---|---|---|
| Question | — (entry in list) | `factory/questions.md` | Orchestrator (from reports) |
| Defect | `templates/defect.md` | `factory/defects/DEF-###.md` | Orchestrator (from reports) |
| Change request | `templates/change-request.md` | `factory/changes/CR-###.md` | Orchestrator |
| Decision (ADR) | `templates/decision.md` | `factory/decisions/DEC-###.md` | Architecture or Design Agent |
| Test report | `templates/test-report.md` | `factory/verification/<level>/report.md` | Unit, Integration, or System Test Agent |
| Acceptance test specification | `templates/test-spec.md` | `factory/acceptance/acceptance-tests.md` | Acceptance Agent |
| Acceptance report (with verdict table) | `templates/acceptance-report.md` | `factory/acceptance/acceptance-report.md` | Acceptance Agent |
| Persistent project memory | `templates/memory.md` | `factory/memory.md` | Memory Agent, called by the Orchestrator |

## Log

The orchestrator appends one line per event to `factory/log.md`:

```
2026-11-21T11:40Z | WO-7 | design-agent | done | DES-010..DES-018 created for ARCH-002 | gate design: pass
```

## Mode-specific completion and dispatch safety

| Work-order mode | Completion evidence |
|---|---|
| `review` | Findings from a read-only review of the inputs. No execution gate is required |
| `specify` | Complete cases, exact sources for expected results, and a passing `trace_check --gate <test-level> --phase specify` check. Code, automation, coverage, and verdicts are not required |
| `author` / `revise` / `fix` | For stage work, the relevant left-side checklist, limited to the component where applicable. G4 uses Implementation regression before unit automation is complete. Memory author/revise work uses its support completion criteria below |
| `execute` | Automated cases, observed results, reports, coverage where applicable, and a passing check in the default execute phase |

For work orders covering a component's design, implementation, or unit tests, append `--scope ARCH-###`. This only establishes that the component is ready to move forward. Aggregate gates always use execute checks without a scope restriction. Specify checks validate the paired left-side artifacts and the requested test specification. They do not require the other verification levels or generate the acceptance matrix.

Before assigning work, the orchestrator saves an active-work-order record. It lists the exact files the agent may write, rather than just their parent directory, along with the starting file hashes, index state, untracked-file state, ID ranges, chosen commands, and source paths for coverage. Record missing files explicitly, and protect existing human changes. Parallel orders must use files that do not overlap. Work on shared configuration and aggregate reports happens one order at a time. Preserve unexpected changes until they can be reconciled; never automatically revert them.

The orchestrator allocates IDs, updates the counters that record the highest reserved numbers, and saves the ranges before assigning work. Agents never choose IDs from a shared "next available" number. If an agent uses up its range, it returns partial. Unused numbers stay reserved even when work is interrupted or cancelled.

A specification or component report cannot claim that an aggregate gate has passed. If the first test automation is deferred, record it as pending verification. A stage closes only when its own automated cases run. Acceptance and CR closure allow no required checks to remain pending. Evidence records the tested build/revision, commands, collected counts, source files included in coverage, and results. A comment tag establishes traceability only.

## Memory work orders and reports

The Memory Agent uses the same work order and report structures in author, revise, or review mode. Its scope is the pending events and named source records; its only write path is `factory/memory.md`. It cites existing IDs and revisions instead of allocating memory IDs. Review is read-only. Gate checks, test commands, and coverage are not applicable to this support task. Its self-check instead covers source accuracy, purpose, condensed history, causes, regression guards, unresolved gaps, and the 1,200-word target.

The work order includes exact pending-event references, source paths and revisions, relevant validated reports, and the starting memory snapshot. The report lists the events actually reconciled, material sources used, changes to lessons, and any uncertainty or missing evidence. Only the orchestrator validates that report and updates the memory progress fields in state. It retains unresolved events rather than declaring the whole summary current. Memory reports do not trigger V-model gate evaluation.

The full memory may contain details that a verifying agent is forbidden to read. The orchestrator filters excerpts by their original sources. A summary cannot turn implementation behavior into an allowed test oracle.

## Bug-fix evidence

Every bug fix includes an automated regression test for the original triggering condition. The test owner adds or extends the case and records its test ID/path, or its tooling test name, along with the fixture or injected fault, expected result from the authoritative specification, buggy revision and expected failing result, fixed revision and passing result, and the required suite results. A routed regression reproduction may run against the buggy build before ordinary execution prerequisites; it cannot close a gate while failing.

The fix owner reports the confirmed root cause and correction. The orchestrator retains the evidence in the defect record and calls the Memory Agent to summarize the lesson and what to check if it recurs. If the condition cannot yet be reproduced or tested, verification remains pending. Existing tests count only when they cover the exact original condition and have the required before/after evidence. Do not reset the shared workspace to obtain that evidence. A green suite or a memory note alone cannot close a bug as fixed.
