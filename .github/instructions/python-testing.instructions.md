---
description: "Python pytest conventions for this monorepo: async FastAPI services, fixtures, naming, mocking, coverage. Use when writing, reviewing or scaffolding test files."
applyTo: "**/tests/**/*.py,**/conftest.py"
---

# Python Testing Conventions

## Project Layout

```
services/
  <svc>/
    app/           # production code
    tests/         # NO __init__.py — uses importlib import mode
      conftest.py
      test_<module>.py
```

- **No `__init__.py`** in test directories (pytest importlib mode handles isolation).
- One `conftest.py` per service; shared fixtures do NOT cross service boundaries.
- Test files: `test_<module_name>.py` matching the source module they exercise.

## pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"          # all async def test_* run without decorator
addopts      = "--import-mode=importlib --cov=services --cov-report=term-missing"
testpaths    = ["services"]

[tool.coverage.report]
fail_under = 80
```

## Naming

Pattern: **`test_<unit>_<scenario>_<expected_outcome>`**

| Part | Example |
|---|---|
| unit | `login`, `transcribe`, `ready` |
| scenario | `wrong_password`, `missing_auth`, `redis_down` |
| expected | `returns_401`, `returns_202`, `returns_not_ready` |

Full examples:
```python
async def test_login_wrong_password_returns_401(...): ...
async def test_transcribe_missing_auth_returns_4xx(...): ...
async def test_ready_redis_degraded_returns_not_ready(...): ...
```

## Given / When / Then (internal structure)

Use `# Given`, `# When`, `# Then` comment blocks **inside** the test body when the test has non-trivial setup. Skip them for trivial two-liner tests — the blocks would only add noise.

**When to add GWT blocks:**
- Explicit state setup beyond fixtures (mocking side-effects, seeding Redis, multi-step flows)
- The test body has three distinct phases worth labelling

**When to omit:**
- Single call + single assert (entire test is 3 lines)
- The `# Given` would only read `# Given: nothing (fixtures do it all)`

```python
# ✅ GWT adds value — non-trivial setup
async def test_ready_redis_degraded_returns_not_ready(
    client: AsyncClient, fake_redis: FakeRedis, mocker: MockerFixture
) -> None:
    # Given: Redis ping raises ConnectionError
    mocker.patch.object(fake_redis, "ping", AsyncMock(side_effect=ConnectionError("down")))

    # When
    response = await client.get("/ready")

    # Then
    assert response.status_code == 200
    assert response.json()["status"] == "not_ready"


# ✅ GWT omitted — trivial
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## conftest.py Structure

Follow this order in every service `conftest.py`:

```
1. sys.path manipulation (required for monorepo isolation)
2. os.environ.setdefault (BEFORE any app import)
3. App imports (AFTER env vars)
4. autouse fixtures (_clear_settings_cache)
5. Infrastructure fixtures (fake_redis, mock_qdrant)
6. Domain fixtures (fake_user, worker_settings)
7. HTTP client fixtures (client, auth_client)
```

### Monorepo isolation pattern

```python
import pathlib, sys
_SERVICE_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
for _k in list(sys.modules):
    if _k == "app" or _k.startswith("app."):
        del sys.modules[_k]
if _SERVICE_ROOT not in sys.path:
    sys.path.insert(0, _SERVICE_ROOT)

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-32chars!!")

from app.config import get_settings  # noqa: E402
```

### Settings cache isolation (autouse)

```python
@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Generator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

## Fixtures

### Scope selection

| Scope | When |
|---|---|
| `function` (default) | Stateful objects: FakeRedis, mock clients, HTTP clients |
| `module` | Heavy read-only objects: parsed config, compiled schemas |
| `session` | Truly immutable: constants, compiled regex |

### Composition over duplication

Build layered fixtures instead of copy-pasting setup. The `auth_client`
composes on `client` — only adds what's different:

```python
@pytest.fixture
async def client(fake_redis, mock_qdrant) -> AsyncGenerator[AsyncClient]:
    app.state.redis = fake_redis
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_qdrant] = lambda: mock_qdrant
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        for attr in ("redis", "qdrant"):
            if hasattr(app.state, attr):
                delattr(app.state, attr)

@pytest.fixture
async def auth_client(client: AsyncClient, fake_user: TokenData) -> AsyncGenerator[AsyncClient]:
    """Composes on client — adds only the auth override."""
    app.dependency_overrides[get_current_user] = lambda: fake_user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
```

### Infrastructure stubs

```python
@pytest.fixture
def fake_redis() -> FakeRedis:
    """fakeredis — full Redis API, no infrastructure."""
    return FakeRedis(decode_responses=True)   # from fakeredis.aioredis

@pytest.fixture
def mock_qdrant() -> MagicMock:
    """Spec-checked stub prevents attribute typos."""
    client = MagicMock(spec=AsyncQdrantClient)
    client.query        = AsyncMock(return_value=[])
    client.add          = AsyncMock(return_value=["test-id"])
    client.get_collections = AsyncMock(return_value=MagicMock(collections=[]))
    client.close        = AsyncMock()
    client.set_model    = MagicMock()   # sync method
    return client
```

## Parametrize

Use `@pytest.mark.parametrize` when the same assertion applies to multiple
inputs. Always provide human-readable `ids=`:

```python
@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("admin", "wrong!"),
        ("nobody", "demo-password"),
        ("", "demo-password"),
    ],
    ids=["wrong-password", "wrong-username", "empty-username"],
)
async def test_login_invalid_credentials_returns_401(
    client: AsyncClient, username: str, password: str
) -> None:
    response = await client.post(
        "/auth/token", json={"username": username, "password": password}
    )
    assert response.status_code == 401
```

## Mocking

### Type annotations — always use `MockerFixture`

```python
from pytest_mock import MockerFixture

async def test_ready_redis_degraded(
    client: AsyncClient, fake_redis: FakeRedis, mocker: MockerFixture
) -> None:
    mocker.patch.object(fake_redis, "ping", AsyncMock(side_effect=ConnectionError("down")))
```

> `pytest.MonkeyPatch` is a different fixture. `mocker` comes from `pytest-mock` and its type is `MockerFixture`.

### Mock preference hierarchy

1. **`fakeredis`** — for Redis (stateful, full API, zero infrastructure)
2. **`MagicMock(spec=AsyncQdrantClient)`** — spec prevents typos, AsyncMock for async methods
3. **`app.dependency_overrides`** — preferred for FastAPI deps (no module patching)
4. **`mocker.patch.object`** — for methods on already-injected stubs
5. **`mocker.patch`** — last resort, for module-level globals

### Assert calls, not just call counts

```python
# Bad
assert mock_qdrant.add.called

# Good
mock_qdrant.add.assert_called_once_with(
    collection_name="transcriptions",
    documents=["hello world"],
    ids=[job_id],
    metadata=[{"user": "testuser"}],
)
```

## Async / ASGI

- Use `httpx.AsyncClient` with `ASGITransport` — no real HTTP server.
- `ASGITransport` does **NOT** call lifespan events. Inject `app.state.*` directly.
- `ASGITransport(raise_app_exceptions=True)` (default): unhandled app exceptions propagate to the test caller; use `pytest.raises(...)` to assert them.

```python
async with AsyncClient(
    transport=ASGITransport(app=app), base_url="http://test"
) as ac:
    ...
```

If you need lifespan events in tests, use `asgi-lifespan`'s `LifespanManager`.

## Coverage

- Gate: **≥ 80 %** (`fail_under = 80` in `[tool.coverage.report]`).
- Lines that are unreachable in tests use `# pragma: no cover`.
- Do not write tests purely to hit coverage — write tests for behaviour.

## Anti-patterns

| Anti-pattern | Correct alternative |
|---|---|
| `mocker: pytest.MonkeyPatch` | `mocker: MockerFixture` |
| `__init__.py` in test dirs | Remove; use `--import-mode=importlib` |
| Duplicate setup in `auth_client` | Compose on `client` fixture |
| `assert mock.called` | `assert_called_once_with(...)` |
| `try/except CancelledError: pass` | `contextlib.suppress(asyncio.CancelledError)` |
| Mutable fixture at `session` scope | Use `function` scope for stateful objects |
| `import app.*` at module level in test files | Import inside fixtures when collision risk exists |
