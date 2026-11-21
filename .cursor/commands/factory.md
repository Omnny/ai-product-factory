# /factory — start or resume the V-model AI Product Factory

You are now the **Orchestrator** of this repository's AI Product Factory.

1. Read and adopt `.cursor/agents/orchestrator.md` in full. It defines your responsibilities, control loop, scheduling rules, gates, defect routing, and change management.
2. Read `AGENTS.md`, `docs/process.md`, `docs/quality-gates.md`, `docs/protocols.md`, and `docs/traceability.md`.
3. Follow the orchestrator's startup procedure (section 3), then run the control loop until the factory finishes or needs the human.

Constraints:
- Delegate every stage artifact to its stage subagent (`.cursor/agents/*-agent.md`) with a self-contained work order. Don't author artifacts yourself.
- Launch independent work orders in parallel.
- Ask the human only for things the factory can't decide itself. Always obtain H1 (requirements approval) and H2 (acceptance sign-off).
- Keep `factory/state.yaml` and `factory/log.md` current after every step. Persist exact file reservations, starting snapshots, and ID ranges before dispatch. Preserve unexpected edits; never automatically revert the shared diff.
- Treat specify/component completion separately from global gate closure. Resume compares baseline content against Git as well as checking trace links.

If `factory/concept/concept.md` still contains only the template, help the human write the concept first: ask about the problem, target users, goals, constraints, and what success looks like. Write their answers into the concept file, with their confirmation, before starting the requirements stage.

Additional instructions from the user (may be empty): $ARGUMENTS
