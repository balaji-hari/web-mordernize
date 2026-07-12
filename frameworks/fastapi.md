---
name: fastapi
display_name: FastAPI (Python 3.12+)
role: target-api
---

## Scaffold

Create `apps/api-new/` and:

1. Drop in `${CLAUDE_PLUGIN_ROOT}/templates/permanent-gotchas/fastapi/pyproject.toml` (the only template the plugin still ships — see `agents/permanent-gotchas.md` hatchling entry for why). Substitute `name = "..."` if the team picked a different project name; **both `only-include` blocks are load-bearing**.
2. Write `app/__init__.py` (empty).
3. Write `app/main.py` with:
   - `CORSMiddleware` against the dev allow-list (`http://localhost:5173`, `http://localhost:3000`, `http://localhost:4200`).
   - `GET /health` returning `{"status": "UP"}`.
   - A `lifespan` async context manager (NO `@app.on_event` — that's deprecated and removed in current FastAPI).
4. Then `cd apps/api-new && pip install -e ".[dev]"`.

## Test framework

`pytest` (default). The pyproject from `templates/permanent-gotchas/fastapi/pyproject.toml` already declares pytest/httpx in `[project.optional-dependencies].dev`, `[tool.pytest.ini_options]`, and `[tool.coverage.run]`. Re-run `pip install -e ".[dev]"` so dev deps land in the venv. Then write:

- `apps/api-new/tests/__init__.py` (empty)
- `apps/api-new/tests/conftest.py` — exports a `client` fixture wrapping the FastAPI app in `httpx.AsyncClient` (or sync `TestClient`) bound to the in-process ASGI transport.
- `apps/api-new/tests/test_health.py` — single test calling `client.get("/health")` and asserting `200` + `{"status": "UP"}`.

Test smoke: `pytest -q tests/test_health.py`.

## Verify commands

| Check | Command |
|---|---|
| lint | `ruff check ${api_root}` |
| typecheck | `mypy ${api_root}` |
| test | `pytest -q ${target_path}` (run from `${api_root}`) |

## Auth notes

Use **`bcrypt>=4.0`** directly with explicit 72-byte truncation. **DO NOT use `passlib[bcrypt]`** — it crashes on first hash call under bcrypt ≥ 4.x because passlib's `detect_wrap_bug` routine tests with a 73-byte secret, which bcrypt 4 raises on instead of silently truncating. This rule survives a `security.py` rewrite and lives in `agents/permanent-gotchas.md`.

Pattern (in `app/auth/security.py`):
```python
import bcrypt

def hash_password(password: str) -> bytes:
    truncated = password.encode("utf-8")[:72]
    return bcrypt.hashpw(truncated, bcrypt.gensalt())

def verify_password(password: str, hashed: bytes) -> bool:
    truncated = password.encode("utf-8")[:72]
    return bcrypt.checkpw(truncated, hashed)
```

If the team wants arbitrary-length passwords (no 72-byte truncation), use SHA-256 pre-hash before `bcrypt.hashpw` and note that legacy bcrypt hashes won't verify on first login.

Seed dev users via `apps/api-new/scripts/seed_dev_users.py`. Run with `python scripts/seed_dev_users.py`. Gate on `os.environ.get("APP_ENV") != "production"` (or equivalent env var).

Refer to `agents/permanent-gotchas.md` for cross-cutting auth rules.

## Data migration

Apply: `alembic upgrade head`
Status (read-only reachability probe): `alembic current`

## Dev server

| Dev port | Install/activate | Dev command | URL | Health check |
|---|---|---|---|---|
| 8000 | `python -m venv .venv && source .venv/bin/activate` *(Windows PowerShell: `.venv\Scripts\Activate.ps1`; bash-on-Windows / Git Bash: `source .venv/Scripts/activate`)*, then `pip install -e ".[dev]"` | `fastapi dev app/main.py` *(or `uvicorn app.main:app --reload`)* | http://localhost:8000 | `curl http://localhost:8000/health` |

## Recommendation context

Smallest jump for teams that want Python on the backend. Async-first, typed, and the OpenAPI generation is excellent. Pairs cleanly with any UI framework.
