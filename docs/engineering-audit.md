# Engineering Audit (Phase 9)

Date: 2026-05-15
Scope: runtime, step SDK, steps, pipelines, infra, CLI DX

## Method

- Source review of core runtime and CLI modules.
- Consistency checks against current docs and command surfaces.
- Operational checks from project baseline (`make ci`, CLI smoke outputs).

## Findings

### High

1. README CLI surface is stale against implementation.
- Evidence: [README.md](../README.md) lists only `init`, `task list`, `step list`, `pipeline list/validate`.
- Evidence: [tools/inferflow-cli/inferflow_cli/main.py](../tools/inferflow-cli/inferflow_cli/main.py) exposes additional groups and commands (`models`, `job`, `pipeline run/deploy/status/logs/scale/rollback/metrics`, `task show/new`, `step new/test/build/push/show`).
- Impact: users underuse capabilities and assume missing features.
- Action: update README to point to a single quickstart + command reference workflow.

2. CLI run path had compatibility fallback coupled to one legacy pipeline.
- Evidence: `pipeline run` previously fallbacked for `audio-rag` to `/transcribe` endpoint.
- Impact: hidden behavior branch, harder to reason about for new pipelines.
- Resolution (2026-05-15): removed implicit fallback from CLI; runtime entrypoint is now explicit and uniform.

### Medium

1. Repository onboarding path is split across README and multiple docs.
- Evidence: setup exists in README and [docs/local-setup.md](local-setup.md), plus demo in [scripts/demo.sh](../scripts/demo.sh).
- Impact: first-time users jump between files before first success.
- Action: single canonical quickstart in [docs/quickstart.md](quickstart.md), README points there.

2. Top-level structure has mixed intent for platform vs product artifacts.
- Evidence: `infra/`, `monitoring/`, and `docs/` all contain operational assets, but ownership boundaries are implicit.
- Impact: harder placement decisions for new contributors.
- Action: publish canonical structure map in [docs/repo-structure.md](repo-structure.md) and follow it for new additions.

### Low

1. CLI help rendering in non-interactive capture is brittle under output filters.
- Evidence: rich help output can be empty when redirected through token filters.
- Impact: CI-like smoke captures are less reliable.
- Action: add smoke checks based on command execution (not only help rendering), and optional plain-text `--help-plain` in future.

## Resolved During Audit

- Removed stale duplicate folder `infra/helm/audiomind` (untracked copy).
- Fixed ruff TC003 in CLI IO module.
- Removed implicit legacy fallback in `inferflow pipeline run`.
- Added CLI smoke tests (F9-6): 8/8 passing - covers help, task discovery, pipeline validation (positive + negative), error clarity.

## Recommended Next Patch Set

1. ✅ Align README CLI section with current command surface. (DONE — expanded in last session)
2. ✅ Add CLI smoke tests. (DONE — 8 tests, 100% pass rate)
3. Execute clean-environment quickstart test to validate end-to-end onboarding flow.
4. Final README polish: ensure <10 min first-run clarity for new developers.
