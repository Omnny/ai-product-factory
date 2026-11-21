# /factory-change — submit a change request to the factory

You are the **Orchestrator** (adopt `.cursor/agents/orchestrator.md`). The human requests this change:

> $ARGUMENTS

Run change management as defined in section 10 of the orchestrator spec:

1. Create `factory/changes/CR-###.md` from `templates/change-request.md`, quoting the request verbatim.
2. Send a review work order to the Requirements Agent to decide which CON, UC, US, REQ, and SCN items change, are added, or are retired. If the request is purely technical (no behavior change a user could observe), have the Architecture or Design Agent identify the directly affected ARCH, IF, or DES items instead.
3. Run `python3 scripts/trace_check.py --impact <directly affected IDs>` and record the downstream impact set in the CR.
4. Show the human the impact summary: affected items per stage, the expected rework, and any new questions. Get approval if scope or behavior a user could observe changes.
5. Invalidate the affected items in `factory/state.yaml` and issue scoped revise work orders top-down. Then re-verify with the suite the impact requires (fast when it stays inside the edited units, slow when it reaches another component, an interface, a scenario, or a requirement; see `AGENTS.md`). Repeat acceptance for the affected CON and REQ items (H2 again if acceptance was already signed).
6. Close the CR with the new baseline tags.
