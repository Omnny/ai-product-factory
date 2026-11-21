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
| Unit tests + coverage | `<cmd>` | Runs `tests/unit/` only; **line + branch coverage, fail under 100%**. This is the core of the fast suite |
| Integration tests | `<cmd>` | Runs `tests/integration/` only |
| System tests | `<cmd>` | Runs `tests/system/` only, against the complete built and started system |
| Acceptance tests | `<cmd>` | Runs `tests/acceptance/` only, through the product's public entry points |
| Fast suite | `<cmd>` | Default: the unit command. Much faster than the slow suite. List any in-process integration tests added to it, and any slow unit tests left out of it |
| Slow suite | `<cmd>` | Fast suite, then integration, system, and acceptance, in that order. A level with no tests yet passes. This is the regression run (`AGENTS.md`) |
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
- **Python:** fast: `pytest tests/unit --cov=src --cov-branch --cov-fail-under=100`; slow: `pytest tests/unit tests/integration tests/system tests/acceptance`; `ruff check . && ruff format --check .`; `mypy src`
- **TypeScript:** `vitest run tests/unit --coverage` (thresholds 100 in `vitest.config.ts`); `eslint . && prettier --check .`; `tsc --noEmit`
- **Go:** `go test ./... -coverprofile=cover.out` + a branch-coverage tool; `golangci-lint run`
