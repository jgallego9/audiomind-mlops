# Adding a Step

## 1. Define or reuse a task schema

Add task schema in `tasks/<task>/schema.json` if the contract is new.

## 2. Scaffold step package

Create `steps/<task>-<impl>/` with:
- `app/config.py`
- `app/step.py`
- `app/main.py`
- `step.yaml`
- `tests/`
- `VERSION`

## 3. Validate

Run:

```bash
uv run pytest steps/<task>-<impl>/tests -q
make ci
```
