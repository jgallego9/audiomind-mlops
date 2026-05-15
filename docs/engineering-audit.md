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

### Medium (Resolved in F9)

1. Repository onboarding path was split across docs — **RESOLVED**.
- Evidence: onboarding was scattered between README, old guides, and demo scripts.
- Solution: [docs/quickstart.md](quickstart.md) created as single canonical path; README links it; docs/local-setup.md removed.
- Validation: executed in clean environment (/tmp/inferflow-test-clean) — full path from init to discovery validated in <5 min.

2. Top-level structure is implicit for new contributors — **RESOLVED**.
- Evidence: `services/`, `infra/`, `docs/`, `steps/`, `pipelines/` lack clear placement rules.
- Solution: [docs/repo-structure.md](repo-structure.md) published with taxonomy and placement guidelines.
- Impact: new contributors now have clear guidance for adding modules/steps/pipelines.

### Low (Resolved in F9)

1. CLI help rendering in non-interactive capture is brittle — **RESOLVED**.
- Evidence: rich output can be empty when redirected through token filters (like snip).
- Solution: added 8/8 smoke tests based on command execution output, not just help rendering (F9-6).
- Impact: CLI validation now robust to output filters; journeys tested for real-world use.

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
