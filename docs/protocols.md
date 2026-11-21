# Protocols

Agents only communicate through the orchestrator, using two message types: the **Work Order** (orchestrator to agent) and the **Agent Report** (agent to orchestrator). Persistent records (defects, questions, change requests, decisions) are files created from the templates in `templates/`.

## Work Order (orchestrator → agent)

The orchestrator sends this as the full prompt when it launches a stage subagent. A subagent starts with **no memory** of the conversation, so the work order must be self-contained.

```markdown
# Work Order WO-<n>: <short title>

- **Agent:** <requirements-agent | architecture-agent | design-agent | implementation-agent |
             unit-test-agent | integration-test-agent | system-test-agent | acceptance-agent>
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
<decisions, answers to questions, defect details, prior attempts and why they failed>

## Constraints
- Write only to: <exact reserved files, including reports/config; no overlapping files>
- Reserved IDs: <prefix: inclusive range; request another range in the report if exhausted>
- Starting snapshot: <state active-work-order record; hashes/index/untracked inventory>
- Check phase and scope: <specify|execute; component ARCH IDs or global>
- Commands / coverage source set: <exact toolchain commands and component files>
- Pending verification: <required checks deferred until initial automation exists, or none>
- Iteration budget: <n>
- <anything else: e.g., "do not change public interface IF-003">

## Expected outputs
- <files / IDs to create or update>

## Exit criteria
- <mode-specific checklist below + applicable quality-gate criteria>
- `python3 scripts/trace_check.py --gate <stage> [--phase specify] [--scope ARCH-###]` passes
- <unscoped execution is mandatory when closing an aggregate gate>
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

The orchestrator assigns real numbers to `Q-draft` and `DEF-draft` entries when it records them, so agents never compete for the next ID.

## Modes

| Mode | Meaning |
|---|---|
| `author` | Create the stage artifact from upstream inputs |
| `revise` | Update specific IDs because of a CR, defect, or review finding |
| `review` | Consumer review of an upstream artifact. Read-only; findings come back as defects or questions |
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

## Log

The orchestrator appends one line per event to `factory/log.md`:

```
2026-11-21T11:40Z | WO-7 | design-agent | done | DES-010..DES-018 created for ARCH-002 | gate design: pass
```

## Mode-specific completion and dispatch safety

| Work-order mode | Completion evidence |
|---|---|
| `review` | Read-only findings against the reviewed inputs; no execution gate required |
| `specify` | Case completeness, exact oracle sources, and `trace_check --gate <test-level> --phase specify`; no code, automation, coverage, or verdict required |
| `author` / `revise` / `fix` | Relevant left-side checklist, using component scope where applicable; G4 uses Implementation regression before unit automation is complete |
| `execute` | Automated cases, observed results, reports, coverage where applicable, and the execute check (default phase) |

For component design, implementation, and unit orders append `--scope ARCH-###`. This is intermediate readiness only. Aggregate gates always use unscoped execute checks. Specify checks validate the paired left-side artifacts plus the requested test specification; they do not require other verification levels or generate the acceptance matrix.

Before dispatch, the orchestrator persists an active-work-order record with exact write files (not just a parent directory), starting hashes and index/untracked state, ID ranges, and the chosen commands/coverage source paths. Record missing files explicitly. Existing human changes remain protected. Parallel orders need disjoint files; serialize shared configuration and aggregate reports. Unexpected changes are preserved and reconciled, never automatically reverted.

The orchestrator allocates IDs, advances high-water counters, and persists ranges before dispatch. Agents never allocate from a shared "next available" number. They return partial if a range is exhausted. Keep unused numbers reserved across interruptions and cancellations.

A specification or component report cannot claim an aggregate gate pass. Deferred initial automation is recorded as pending verification. A stage closes only when its own automated cases run; acceptance and CR closure permit no pending required checks. Evidence records the tested build/revision, commands, collected counts, coverage source set, and results; a comment tag establishes traceability only.
