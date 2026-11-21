# <Unit | Integration | System | Acceptance> Test Specification: <scope>

- **Phase:** specify (case readiness only; execution/coverage/verdicts follow later)
- **Reserved IDs / exact output files:** <from work order>
- **Owner:** <Unit Test | Integration Test | System Test | Acceptance> Agent
- **Verifies baseline:** <paired stage tag: implementation (oracle: design) | design | architecture | requirements>
- **Level rules (V-model pairs):**
  - Unit Testing ↔ Implementation: UT verifies DES (each implemented unit; oracle = its unit specification)
  - Integration Testing ↔ Design: IT verifies DES collaborations and internal IF realizations
  - System Testing ↔ Architecture: ST verifies ARCH, external IF, and SCN end to end
  - Acceptance ↔ Requirements: AT verifies REQ (each acceptance criterion)

## Coverage of specification items
| Spec item | Test cases | Nominal | Boundary | Negative | Error/failure |
|---|---|---|---|---|---|
| DES-001 | UT-001..UT-006 | ✓ | ✓ | ✓ | ✓ |

## Test cases

### UT-001: <behavior under condition, e.g., "rejects quantity above 999">
- **Verifies:** DES-001
- **Technique:** nominal | equivalence class | boundary value | decision table | state transition | error path | contract | failure injection | end-to-end scenario | non-functional
- **Preconditions / setup:** <state, fixtures, fakes>
- **Input / stimulus:** <exact values or steps>
- **Expected result:** <exact observable outcome>
- **Oracle source:** <e.g., DES-001 Behavior step 3; ARCH-002 runtime sequence for UC-001; REQ-007 acceptance criterion 2>
- **Automated in:** `tests/<unit|integration|system|acceptance>/<file>` (tag `@test UT-001`)
