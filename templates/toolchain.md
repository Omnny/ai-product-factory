# Toolchain

- **Owner:** Architecture Agent
- **Decisions:** DEC-### (language), DEC-### (test framework), DEC-### (coverage tool)

Every agent builds, runs, and tests the product **only** through these commands. Run them from the repository root.

| Purpose | Command | Notes |
|---|---|---|
| Setup / install | `<cmd>` | Must work from a clean checkout |
| Build | `<cmd>` | |
| Lint + format check | `<cmd>` | Zero warnings policy |
| Type check | `<cmd>` | If applicable |
| Implementation regression | `<cmd>` | Existing unit automation, no coverage threshold on newly implemented units. Zero tests may be deferred only before initial automation; never masks a missing established suite |
| Component unit tests + coverage | `<cmd per ARCH>` | Exact test selectors and complete source-file set per component; fail under 100% line and branch coverage |
| Unit tests + coverage | `<cmd>` | Runs `tests/unit/` only; **line + branch coverage, fail under 100%**. This is the core of the fast suite |
| Integration tests | `<cmd>` | Runs `tests/integration/` only |
| System tests | `<cmd>` | Runs `tests/system/` only, against the complete built and started system |
| Acceptance tests | `<cmd>` | Runs `tests/acceptance/` only, through the product's public entry points |
| Fast suite | `<cmd>` | Default: the unit command. Much faster than the slow suite. List any in-process integration tests added to it, and any slow unit tests left out of it |
| Slow suite | `<cmd>` | Fast suite, then integration, system, and acceptance, in that order. Before a level's initial execute order, missing automation is deferred, never marked passed; once automation exists, zero collected tests fails. G8 permits no deferrals. This is the regression run (`AGENTS.md`) |
| Run product | `<cmd>` | How a user starts it |
| Mutation testing (optional) | `<cmd>` | |

## Coverage
- Report location: `<path>`
- Exclusion syntax: `<e.g., # pragma: no cover>`. Allowed only with an accepted `DEC-###` cited on the same line.

## Conventions
- Source layout: `src/<...>`
- Test naming: `<pattern>`
- Tag comment style: `<e.g., # @implements DES-001 / // @test UT-001>`

## Examples (pick one family, delete the rest)
- **Python:** fast: `pytest tests/unit --cov=src --cov-branch --cov-fail-under=100`; implementation regression: `pytest tests/unit` (before initial automation, explicitly record zero collection as deferred); slow: run the fast coverage command successfully first, then the integration, system, and acceptance commands sequentially, stopping on failure; `ruff check . && ruff format --check .`; `mypy src`
- **TypeScript:** `vitest run tests/unit --coverage` (thresholds 100 in `vitest.config.ts`); `eslint . && prettier --check .`; `tsc --noEmit`
- **Go:** `go test ./... -coverprofile=cover.out` + a branch-coverage tool; `golangci-lint run`

## Component selectors and evidence
| Component | Source files included in coverage | Unit test selector | Unit command with 100% thresholds |
|---|---|---|---|
| ARCH-### | `<complete owned file set>` | `<selector>` | `<command>` |

The global fast command covers all `src/` before aggregate G5 closes. Implementation regression has no new-unit coverage threshold so G4 can precede initial test automation. Product test runners must fail on zero collection once that level has automation; do not turn arbitrary nonzero exits into success. The slow command must stop on a failed lower level, preserve unit coverage enforcement, and report deferred higher levels explicitly. Record each actually executed level and the tested source revision in reports. A report from another revision is stale.
