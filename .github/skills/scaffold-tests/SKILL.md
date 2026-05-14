---
name: scaffold-tests
description: "Scaffold pytest test suite for a new service in this monorepo. Use when adding a new FastAPI service or async worker and needing conftest.py + test_*.py files. Generates: conftest with fakeredis/mock_qdrant fixtures, client/auth_client pattern, and test stubs for health, auth, and domain endpoints."
argument-hint: "Service name, e.g. 'notification-service'"
---

# Scaffold Tests for a New Service

## When to Use

- Adding a new FastAPI service under `services/<svc>/`
- Adding a new async worker service
- Refreshing a test suite that doesn't follow monorepo conventions

## Procedure

### 1. Gather context

Read the service's `app/main.py` and `app/config.py` to identify:
- Settings class and required env vars
- Dependency functions (`get_redis`, `get_qdrant`, custom deps)
- Route modules and their prefixes
- `app.state.*` attributes set in the lifespan

### 2. Create `services/<svc>/tests/conftest.py`

Use the [conftest template](./templates/conftest.py.md).

Key rules:
- **No `__init__.py`** in the tests directory
- `sys.path` manipulation comes first, before any app import
- `os.environ.setdefault` for every required setting without a default
- `autouse` fixture clears the `@lru_cache` on `get_settings`
- `fake_redis = FakeRedis(decode_responses=True)` from `fakeredis.aioredis`
- `mock_qdrant = MagicMock(spec=AsyncQdrantClient)` with AsyncMock methods
- `client` fixture: sets `app.state.*`, overrides deps, yields `AsyncClient`, cleans up in `finally`
- `auth_client` fixture: composes on `client`, adds only `get_current_user` override

### 3. Create test files

One file per route module:

| Route module | Test file |
|---|---|
| `routes/health.py` | `test_health.py` |
| `routes/auth.py` | `test_auth.py` |
| `routes/jobs.py` | `test_jobs.py` |
| `routes/search.py` | `test_search.py` |
| `consumer.py` | `test_consumer.py` |
| `indexer.py` | `test_indexer.py` |

### 4. Naming convention

```
test_<unit>_<scenario>_<expected_outcome>
```

Examples:
- `test_health_returns_ok`
- `test_login_wrong_password_returns_401`
- `test_transcribe_no_auth_returns_4xx`

### 5. Mandatory test coverage per layer

**Health endpoints** (`test_health.py`):
- `GET /health` → 200, `status == "ok"`
- `GET /ready` → all deps ok → `status == "ready"`
- `GET /ready` → redis down → `status == "not_ready"`
- `GET /ready` → qdrant down → `status == "not_ready"`
- `GET /ready` → `latency_ms` field present

**Auth endpoints** (`test_auth.py`):
- Login with valid credentials → 200, token present
- `@pytest.mark.parametrize` for invalid credentials (wrong password, wrong username, empty)
- Missing body → 422
- End-to-end: get token → use on authenticated endpoint
- Tampered token → 401
- Missing Authorization header → `in {401, 403}`

**Job/domain endpoints**:
- Happy path (202/200, correct body shape)
- State stored in fake_redis (hgetall verification)
- Stream published (xrange verification)
- Invalid input → 422
- No auth → `in {401, 403}`
- 404 for missing resources

**Search endpoints**:
- Results returned with correct shape
- Empty collection (404 from Qdrant) → empty results, not error
- 5xx from Qdrant → `pytest.raises(UnexpectedResponse)` (re-raised by route)
- Filter applied with correct user context
- Query too long / empty → 422

### 6. Run and verify

```bash
uv run pytest services/<svc>/tests/ -v
uv run pytest services/ -q   # full suite — check combined coverage ≥ 80%
```

### 7. Lint

```bash
uv run ruff check services/<svc>/tests/
uv run ruff format services/<svc>/tests/
```

## References

- [conftest template](./templates/conftest.py.md)
- [python-testing instructions](../../instructions/python-testing.instructions.md)
- [pytest good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [FastAPI async tests](https://fastapi.tiangolo.com/advanced/async-tests/)
