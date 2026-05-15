# Local Setup

## Requirements

- Python 3.13+
- uv
- Docker + Compose

## Install dependencies

```bash
uv sync --all-packages --dev
```

## Initialize project config

```bash
uv tool install ./tools/inferflow-cli
inferflow init
```

## Validate baseline

```bash
make ci
```
