# MoiraWeave Core

Runtime repository for the MoiraWeave platform.

## What lives here

- `services/`: API gateway, workers, shared schemas, and the step SDK.
- `infra/`: Helm, Kubernetes, kind, and Terraform configuration.
- `monitoring/`: observability assets consumed by the runtime stack.
- `pipelines/`: declarative pipeline definitions used by the runtime.
- `tests/`: integration and cross-service validation.

## Companion repositories

- [moiraweave-steps](https://github.com/moiraweave-labs/moiraweave-steps) for step implementations and task schemas.
- [moiraweave-cli](https://github.com/moiraweave-labs/moiraweave-cli) for the developer CLI.
- [moiraweave-docs](https://github.com/moiraweave-labs/moiraweave-docs) for the public documentation site.
- [.github](https://github.com/moiraweave-labs/.github) for organization-wide templates and policies.

## Local validation

```bash
uv sync --frozen --all-packages
make ci
```

## Releases

This repository owns runtime images, Helm packaging, and platform release automation.

