# Quickstart (Phase 9)

Goal: first successful local run with minimal decisions.

## 1. Prerequisites

- Python 3.13+
- `uv`
- Docker with Compose
- `curl` and `jq`

## 2. Install and initialize

```bash
git clone <repo-url>
cd moiraweave-mlops
uv sync --all-packages --dev
uv tool install ./tools/moira-cli
moira init --non-interactive
```

## 3. Start local stack

```bash
docker compose up -d
```

Validate health:

```bash
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/ready | jq
```

## 4. Validate a pipeline contract

```bash
moira pipeline list
moira pipeline validate image-search
```

## 5. Run end-to-end demo

```bash
bash scripts/demo.sh
```

Expected result:

- job is created and reaches `completed`
- transcript preview is printed
- semantic search returns at least one result

## 6. Optional quality gate

```bash
make ci
```

## Troubleshooting

- If `moira` command is not found, ensure `uv tool install ./tools/moira-cli` completed.
- If `/ready` is not ready, wait for dependencies and retry.
- If demo auth fails, check `.env` values and service logs:

```bash
docker compose logs --tail=200 api-gateway worker
```
