# Acceptance Report: <product name>

- **Owner:** Acceptance Agent
- **Verifies:** Requirements baseline <tag>
- **Build / commit:** <hash>
- **Date:** <ISO date>
- **Recommendation:** accept | accept with conditions | reject

## 1. What the product does
<Plain-language summary for a non-engineer.>

## 2. How to run it
<Exact commands from toolchain.md, verified from a clean checkout.>

## 3. Verification evidence (all four levels, same build)
| Level | Paired with | Total | Passed | Failed | Notes |
|---|---|---|---|---|---|
| Unit Testing | Implementation | | | | coverage line <x>% / branch <y>% |
| Integration Testing | Design | | | | |
| System Testing | Architecture | | | | |
| Acceptance | Requirements | | | | |
| Traceability | — | | | | `trace_check --gate acceptance`: <pass/fail> |

## 4. Verdicts

One row per concept goal and per requirement. The traceability checker reads this table: the first column is the ID and the second is the verdict (`accepted`, `rejected`, or `waived`). Evidence cites test IDs. A `waived` row cites the human decision in Notes.

| Item | Verdict | Evidence | Notes |
|---|---|---|---|
| CON-001 | accepted | AT-001, AT-002 | Use cases UC-001 (main ✓, ext 2a ✓), US-001 value delivered ✓ |
| REQ-001 | accepted | AT-001, ST-003 | AC1 ✓ AC2 ✓ |
| REQ-002 | waived | — | Q-007: deferred by human to next increment |

## 5. Concept goal assessment
### <CON-001 title>
<Do the accepted requirements together deliver the goal as the human intended? Use cases and guarantees checked; user story value delivered; gaps between intent and requirements.>

## 6. Exploratory findings
- <observation> — proposed CR? yes/no

## 7. Open items
- Open defects: <by severity>
- Unconfirmed assumptions: <...>
- Coverage exclusions: <DEC-###>
- Known limitations / residual risks: <...>

## 8. Human sign-off (H2)
- **Decision:** <accepted / rejected>  **By:** <name>  **Date:** <date>  **Notes:** <...>
