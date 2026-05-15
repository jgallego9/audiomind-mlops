# Repository Structure (Phase 9)

## Current Top-Level Model

- `services/`: runtime services and internal SDKs.
- `steps/`: deployable step implementations.
- `tasks/`: task contracts as shared schemas.
- `pipelines/`: declarative pipeline definitions.
- `infra/`: deploy and platform manifests (helm, k8s, terraform, kind).
- `docs/`: human documentation and assets.
- `tools/`: developer tools (CLI package).
- `scripts/`: operational helper scripts.
- `tests/`: cross-service/integration tests.

## Placement Rules (Canonical)

1. Business/runtime behavior goes under `services/`.
2. Reusable inference units go under `steps/`.
3. Any new contract goes under `tasks/` first, then implementations reference it.
4. Any deploy concern goes under `infra/` (never duplicated in `scripts/`).
5. User-facing documentation goes under `docs/`; README remains a navigational entrypoint.
6. Dev tooling goes under `tools/`; build orchestration remains in root Makefile.

## Recommended Legibility Improvements

1. Keep one canonical quickstart doc and avoid repeated setup sections.
2. Keep architecture deep dives in `docs/`; link from README instead of duplicating large blocks.
3. Treat `monitoring/` as implementation data and document ownership relation to `infra/monitoring` assets.
4. For each new top-level folder proposal, require short rationale in PR description.

## Low-Risk Migration Plan

1. Phase A: documentation alignment only (this phase).
2. Phase B: move/rename directories only when references are fully updated and CI is green.
3. Phase C: cleanup legacy aliases and dead paths after one release cycle.
