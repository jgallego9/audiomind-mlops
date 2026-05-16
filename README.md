# MoiraWeave Core

Runtime and infrastructure repository for the MoiraWeave platform.

## What lives here

- `services/`: API gateway, workers, shared schemas, and the step SDK (platform, not user code).
- `infra/`: Helm, Kubernetes, kind, and Terraform templates for deployment.
- `monitoring/`: observability assets consumed by the runtime stack.
- `pipelines/`: reference pipeline definitions for testing and documentation.
- `tests/`: integration and cross-service validation.

## What does NOT live here

- **User pipelines**: You create and manage pipelines in your own workspace repo.
- **User custom steps**: You develop custom steps in your own workspace, not here.
- **User configuration**: Environment-specific config (moiraweave.yaml, .env, deploy overlays) belongs in your workspace.

## For Users: Getting Started

You do not need to clone this repository for normal usage. Instead:

1. Install the CLI: `uv tool install git+https://github.com/moiraweave-labs/moiraweave-cli`
2. Create your workspace: `moira project init`
3. Define your pipelines and steps in your workspace.

This repository is a reference for:
- Understanding the runtime architecture.
- Contributing to the platform core.
- Customizing Helm/K8s/Terraform templates (via `moira` CLI or direct overlay in your workspace).

## Local Development (Contributors)

```bash
uv sync --frozen --all-packages
make ci
```

## Releases

This repository owns runtime images, Helm packaging, and platform release automation.

## Companion repositories

- [moiraweave-steps](https://github.com/moiraweave-labs/moiraweave-steps): Official step catalog (optional, consumed by reference).
- [moiraweave-cli](https://github.com/moiraweave-labs/moiraweave-cli): Developer CLI (your entry point).
- [moiraweave-docs](https://github.com/moiraweave-labs/moiraweave-docs): Documentation.
- [.github](https://github.com/moiraweave-labs/.github): Org-wide templates and policies.

