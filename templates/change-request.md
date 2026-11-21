# CR-###: <short title>

- **Status:** proposed | approved | in_progress | verified | closed | rejected
- **Requested by:** <human | DEF-### | review>
- **Date:** <ISO date>
- **Human approval required:** yes | no — <reason>

## Request
> <verbatim request>

## Directly affected items
| ID | Change | Description |
|---|---|---|
| REQ-### | modify / add / retire | <...> |

## Impact analysis
Output of `python3 scripts/trace_check.py --impact <IDs>`:

| Stage | Revision candidates (impact) |
|---|---|
| Requirements | |
| Architecture | |
| Design | |
| Code | |
| Unit tests | |
| Integration tests | |
| System tests | |
| Acceptance | |

### Regression candidates (verification only)
<Store the separate `regression` output and `minimum_suite`; explain any broader suite required by behavior or accumulated changes. Higher-level tests being selected does not itself change their specifications.>

## Plan
1. WO-<n>: <agent> revise <IDs>
2. ...

## Verification
- Affected tests re-run: <results>
- Full regression: <results>
- Acceptance re-evaluated: <AT IDs>

## Closure
- New baselines: <tags>
