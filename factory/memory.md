# Project Memory

- **Sources reviewed through:** committed history through `159fee2`; the current memory-agent maintenance change awaits its first agent reconciliation
- **Events reviewed:** initial maintainer review of the README, state, Git history, and checker regression cases
- **Review status:** pending reconciliation, recorded in [state](state.yaml); historical before/after reports were not retained

## Purpose and boundaries

This repository is a Cursor-native AI Product Factory starter. Eight specialized stage agents work through the V-model, coordinated by a top-level orchestrator. Requirements pair with Acceptance, Architecture with System Testing, Design with Integration Testing, and Implementation with Unit Testing. The factory maintains traceability and separates implementation from independent verification. See the [README](../README.md) and [factory rules](../AGENTS.md).

The Memory Agent supports the orchestrator by preserving a condensed account of purpose, build history, important causes, and regression guards. It is not a ninth stage. The [product concept](concept/concept.md) is still a template, so the purpose and scope of a product to be generated have not been defined.

## Current position

The repository contains agent instructions, artifact templates, process documentation, and a Python traceability checker. Product source and all four product test directories contain placeholders. [State](state.yaml) records increment 1, an unready concept, and no started or accepted product stage. No generated product or acceptance sign-off is recorded.

The memory integration adds one support agent and a required original-condition regression rule for bug fixes. Its initial summary needs reconciliation by the Memory Agent when the orchestrator next starts. Exact progress and pending events remain in state.

## Build history

| Milestone | What changed and why | Evidence |
|---|---|---|
| `ea831bf` | Initialized the V-model starter with stage agents, templates, process records, and trace tooling | Git history; [agent specifications](../.cursor/agents/orchestrator.md) |
| `000aef8` | Added Conventional Commits and fast/slow product suites so small changes can be checked quickly while broader regression remains required | Git history; [factory rules](../AGENTS.md) |
| `875fd5d` | Corrected workflow and checker gaps involving test specification, component checks, impact analysis, baseline integrity, and acceptance evidence; added regression coverage | Git diff for this commit; [checker](../scripts/trace_check.py); [checker tests](../scripts/test_trace_check.py) |
| `159fee2` | Reworded the README and supporting documentation to match the author's explanatory style while preserving their technical content | Git history and diff for this commit |

## Issues, root causes, and regression guards

These are historical checker and workflow findings from `875fd5d`, rather than invented product defect records. The current tests retain executable guards. Dedicated failing-before/passing-after reports were not retained, so that evidence remains a gap under the new defect-closure rule.

| Issue and original condition | Root cause and correction | Regression guard and evidence | What to check if it recurs |
|---|---|---|---|
| Test specifications written before code, or a ready component beside a pending sibling, could not pass their checks | Execution-only and whole-project obligations were applied to intermediate work. Specification phase and component scope now separate those checks; aggregate gates remain strict | `test_each_test_level_can_specify_before_code_or_automation_exists` and `test_component_checks_allow_pending_siblings_but_global_gate_fails` in the checker tests; correction: `875fd5d` | Check phase, component scope, and whether global completion was claimed from an intermediate result |
| Changing a unit omitted callers and broader verification | Declared dependencies were absent from impact traversal. Caller propagation now follows direct and realized-interface dependencies, while regression candidates stay separate from specification rework | `test_dependency_impact_reaches_callers_code_and_their_tests` and `test_provider_impact_reaches_callers_via_realized_interface`; checker tests and `875fd5d` | Review dependency links and required higher-level tests before treating a change as local |
| A behavior change could retain valid trace tags; an index change could also be hidden by a matching working file | Trace validity was being used as evidence of baseline integrity. Git comparison now checks committed content, the working tree, index, and new files in owned paths | `test_baseline_detects_untagged_behavior_change_that_trace_check_cannot` and `test_baseline_detects_index_change_even_when_worktree_matches_baseline`; checker tests and `875fd5d` | Compare exact baseline paths and both index and working-tree state; trace success alone is insufficient |
| Acceptance could pass with an empty Evidence cell and an ID mentioned only in Notes | Verdict parsing collected IDs from the rest of the row. Evidence is now parsed separately and checked for live, relevant test IDs, with a direct AT required for an accepted REQ | `test_notes_cannot_fill_an_empty_evidence_cell` and `test_evidence_must_be_live_relevant_tests_in_the_evidence_cell`; checker tests and `875fd5d` | Inspect the Evidence cell itself and the test-to-requirement relationship |

All named guards are in [scripts/test_trace_check.py](../scripts/test_trace_check.py). Run the tooling suite with `python3 -m unittest discover -s scripts -p 'test_*.py'`. These checks are separate from product UT/IT/ST/AT suites.

## Decisions and lessons to retain

Preserve the Cursor-native `.cursor/agents/`, `.cursor/commands/`, and `.cursor/rules/` layout. Keep exactly eight V-model stages. Only the orchestrator coordinates and commits during a run, and only the Memory Agent maintains this summary. See the [orchestrator](../.cursor/agents/orchestrator.md), [Memory Agent](../.cursor/agents/memory-agent.md), and [protocols](../docs/protocols.md).

Parallel work needs exact file reservations and reserved ID ranges. A shared Git diff cannot establish which agent caused a change; preserve unexpected edits instead of automatically reverting them. These process safeguards were recorded in `875fd5d`. Their real execution inside Cursor still needs an end-to-end run.

## Pending questions and verification

The product concept needs human input. An end-to-end Cursor run, including interruption/resume and a change request, is not recorded. Historical before/after regression reports remain missing; do not present this summary as evidence that the new closure protocol was followed retroactively. New bug fixes must retain the original condition, confirmed cause, regression test, and observed before/after results in their defect records before being closed as fixed.

Memory is context for the orchestrator. Primary artifacts and current test results remain authoritative, and excerpts passed to stage agents must respect their information rules.
