# DEF-###: <short title>

- **Status:** open | in_fix | fixed | verified | closed | waived
- **Severity:** critical | major | minor
- **Class:** code | test | design | architecture | requirement | environment
- **Found by:** <agent> in WO-<n>
- **Against:** <IDs and/or paths>
- **Routed to:** <agent>
- **Fix iterations:** 0 / <budget>

## Observed
<Exact failing test(s) / review finding, command, actual output.>

## Expected
<Expected behavior with citation of the specification clause (e.g., DES-004 Behavior step 2; REQ-011 AC1).>

## Steps to reproduce
1. `<command>`

## History
| Date | WO | Agent | Action | Result |
|---|---|---|---|---|

## Resolution
<Root cause, fix summary, verification evidence (test IDs re-run and results).>

## Original condition and confirmed root cause
- **Trigger:** <exact input, state, sequence, boundary, environment, or injected fault that exposed the bug>
- **Root cause:** <why that condition caused the observed failure; cite supporting source and evidence; mark hypotheses as unconfirmed>
- **Correction:** <how the fix removes the cause rather than hiding the symptom>

## Regression guard (required for every bug fix)
- **Test owner:** <appropriate test agent; factory maintainer for tooling/process checks>
- **Case / test:** <UT/IT/ST/AT ID and automated path, or tooling test name/path>
- **Condition covered:** <the original trigger and how the test produces it; include the fixture or fault>
- **Expected result / oracle:** <paired specification clause or authoritative tooling/process contract>
- **Buggy revision and command:** <revision or source snapshot; exact reproduction command>
- **Failing-before evidence:** <observed failure and why it demonstrates this bug rather than a broken environment>
- **Fixed revision and command:** <revision or source snapshot; exact regression command>
- **Passing-after evidence:** <observed passing result for the same condition>
- **Required suite results:** <fast/slow choice and evidence on the changed build>

## Memory handoff
- **Lesson sources:** <this defect, fix revision, tests, and result/report references for the Memory Agent>
- **Recall condition:** <symptoms or conditions that should cause the orchestrator to revisit this issue>
- **Memory work order / status:** <WO reference; pending | reconciled; unresolved gaps>

Do not mark the defect verified or closed as fixed until the original-condition regression evidence is complete and the memory lesson is reconciled. A waived issue is not a verified fix.
