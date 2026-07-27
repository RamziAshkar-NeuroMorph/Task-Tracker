# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is the **Module 4 Task Tracker** course project. It documents the `main` branch only.

## 1. Tech stack

| Piece | What's actually installed in `.venv` |
| --- | --- |
| Python | **3.12.0** — the course says 3.11 and `README.md` says "3.9+". Neither matches the venv. `[VERIFY]` which is authoritative; nothing in the code requires >3.9 except `X \| None` unions and `dict[str, ...]`/`frozenset[...]` generics (3.9+/3.10+). |
| FastAPI | 0.139.0 |
| Pydantic | **v2** (2.13.4) — `ConfigDict`, `field_validator`, `model_dump`, `model_copy` are all v2 APIs. |
| Uvicorn | 0.50.2 (`uvicorn[standard]`) |
| pytest | 9.1.1 |
| httpx | 0.28.1 — **not imported directly by any test.** It is pulled in as the transport for `fastapi.testclient.TestClient`. Starlette 1.3.1 emits a deprecation warning on import asking for `httpx2` instead; the tests still pass. |
| Frontend | Vanilla JavaScript — `frontend/index.html`, one self-contained 1198-line file. No build step, no framework, no npm. |

`requirements.txt` lists only `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv` — **unpinned**, and it omits `pytest` and `httpx`. A fresh `pip install -r requirements.txt` gives you no test runner. `python-dotenv` is listed but unused (see Repository notes).

## 2. Run command

```bash
uvicorn app.main:app --reload --port 8000
```

API at `http://localhost:8000`, Swagger UI at `http://localhost:8000/docs`.

To serve the frontend (must be port 5500 — see CORS below):

```bash
python -m http.server 5500 --directory frontend
```

## 3. Test command

```bash
pytest -v
```

18 tests in `tests/test_tasks.py`. Single test / single file:

```bash
pytest -v tests/test_tasks.py
pytest -v tests/test_tasks.py::test_patch_invalid_transition_todo_to_done_returns_422
```

On Windows without the venv activated, prefix with `.venv/Scripts/python.exe -m` (e.g. `.venv/Scripts/python.exe -m pytest -v`). There is no linter or formatter configured — don't invent one.

## 4. Architecture

### Backend — `app/`

Four modules in strict dependency order: `main` → `business_rules` → `models`, and `main` → `storage` → `models`.

- **`app/main.py`** — FastAPI app, CORS middleware, all routing, all HTTP concerns. Owns every `HTTPException` for 404s. Endpoints: `GET /health`, `POST /tasks` (201), `GET /tasks` (optional `status` / `priority` query filters), `GET /tasks/{task_id}`, `PATCH /tasks/{task_id}`, `DELETE /tasks/{task_id}` (204).
- **`app/business_rules.py`** — **where the task rules live.** The `VALID_TRANSITIONS` table and `validate_status_transition()`. Raises 422 directly.
- **`app/storage.py`** — persistence and query filtering. Returns `None`/`False` on miss; never raises HTTP errors.
- **`app/models.py`** — Pydantic schemas (`TaskCreate`, `TaskUpdate`, `TaskResponse`) and the `TaskStatus` / `TaskPriority` enums. Field-level rules (title validation, `extra="forbid"`) live here.

The layering rule that matters: **storage signals absence by return value, `main.py` translates that into HTTP status.** Adding an exception raise inside `storage.py` would break that split.

### Frontend — `frontend/index.html`

One file, 1198 lines, vanilla JS + inline CSS. A Kanban board with three columns; drag-and-drop moves a card by PATCHing its status, so **the frontend is subject to the transition rules below** and surfaces the 422 detail string as a board notice.

### Tests — `tests/`

- `tests/test_tasks.py` — the 18 real pytest tests.
- `tests/conftest.py` — fixtures: an **autouse** `_reset_storage` calling `storage._reset()` before and after every test, plus `client` (`TestClient`) and `created_task`.
- `tests/verify_a.py` — **not a pytest file**; see Repository notes.

### Storage is in-memory, not file-based

`storage.py` keeps a module-level `_tasks: dict[str, TaskResponse]`. Data does not survive a restart. The FastAPI `description=` string in `main.py` and `README.md` both claim "file-based JSON storage" — that is aspirational (from the ADR), not implemented. Don't trust those strings.

Because state is module-level, any new module-level state added to `storage.py` must also be cleared in `_reset()`, or tests will leak into each other.

## 5. Business rules

### Status values

`TaskStatus` (`app/models.py`) — string enum, exact casing matters on the wire:

- `"ToDo"` (default for a new task)
- `"InProgress"`
- `"Done"`

### Priority values

`TaskPriority` — `"Low"`, `"Medium"` (default), `"High"`. Priority has no transition rules; any value may change to any other.

### Transition rules

`VALID_TRANSITIONS` in `app/business_rules.py` is a `frozenset` of `(from, to)` pairs. Exactly six pairs are allowed; everything else is 422.

| from ↓ / to → | ToDo | InProgress | Done |
| --- | --- | --- | --- |
| **ToDo** | ✅ | ✅ | ❌ |
| **InProgress** | ❌ | ✅ | ✅ |
| **Done** | ❌ | ✅ | ✅ |

The non-obvious parts:

- **Self-transitions are valid and explicitly listed** (`ToDo→ToDo`, `InProgress→InProgress`, `Done→Done`) — a PATCH that re-sends the current status returns 200.
- **`ToDo→Done` is invalid**; work must pass through `InProgress`.
- **`Done→InProgress` is valid** (reopening), but **`Done→ToDo` is not**.
- **Nothing may return to `ToDo`** once it has left.

### How the rule is enforced

`app/main.py:58-62` validates the transition *before* calling `storage.update_task`, re-fetching the task to do so — hence the duplicated 404 check in `update_task`. **Order matters: a nonexistent task yields 404, not 422.** The 422 detail string enumerates the allowed transitions.

The guard is `if payload.status is not None`. Verified consequence: **`PATCH {"status": null}` skips validation entirely and writes `status: null` onto the stored task** (returns 200 with `"status": null`). `model_copy(update=...)` does not re-validate in Pydantic v2, so the corrupt value persists and is served on subsequent GETs. This is a gap, not an intended rule — do not "document" it as behavior, and ask before changing it.

### Other validation rules

- Every model sets `model_config = ConfigDict(extra="forbid")`, so unknown request fields produce a 422 rather than being ignored. This is deliberate and directly tested (`test_create_task_unknown_field_returns_422`). It also means `id` / `created_at` cannot be injected through `TaskCreate` / `TaskUpdate`.
- `title` has a `field_validator` that strips whitespace, rejects blank, and caps at 200 chars. It is duplicated across `TaskCreate` and `TaskUpdate` because the update variant must pass `None` through untouched — keep both in sync.
- `update_task` uses `payload.model_dump(exclude_unset=True)` plus `model_copy(update=...)`. PATCH is genuinely partial: a field omitted from the request body is left alone, which is *not* the same as sending it as `null`. Records are replaced immutably rather than mutated. An empty PATCH body returns the existing task unchanged, without bumping `updated_at`.
- `id` is a `uuid4()` string; `created_at` / `updated_at` are UTC-aware and set by `storage.py`, never by the client.

## 6. UI states and CORS

### UI states

`renderBoard(tasks, state)` in `frontend/index.html` drives four states:

- **`loading`** — `renderLoadingState()`, "Loading tasks…" with `role="status"` / `aria-live="polite"`.
- **`error`** — `renderErrorState()` paints the `#error-overlay` (`role="alert"`, `aria-live="assertive"`) with a **Retry** button (`data-action="retry"`). Deliberately renders **no** empty state — there is a comment at line 843 noting the tasks failed to load, they aren't absent.
- **`empty`** — `renderEmptyState()`, an icon plus a create-task call to action. Chosen via `tasks.length === 0 ? 'empty' : 'ready'`.
- **`ready`** — the three Kanban columns.

Separately: `setFormError()` shows inline validation errors in the create/edit form, and `showBoardNotice()` surfaces a failed drag-and-drop PATCH (including the 422 transition message) above the board.

### CORS

`main.py:14-24` hardcodes an allowlist of exactly four origins:

- `http://localhost:5500`
- `http://127.0.0.1:5500`
- `http://localhost:5173`
- `null` (for `file://` — opening `index.html` directly)

`allow_methods=["*"]`, `allow_headers=["*"]`, no `allow_credentials`. The frontend hardcodes `http://localhost:8000` at several `fetch` call sites. **Serving the frontend from any other port fails on CORS — change both sides together.**

## 7. Do not (without asking first)

- **Do not add authentication or authorization.** No API keys, no JWT, no login. Out of scope by design.
- **Do not add a database or an ORM.** Storage is the in-memory dict in `storage.py`. Not SQLite, not SQLAlchemy, not the "file-based JSON" the README aspires to.
- **Do not add deployment steps.** No Docker, no CI config, no hosting, no reverse proxy.
- **Do not make major UI changes.** `frontend/index.html` stays one self-contained vanilla-JS file: no framework, no build step, no npm, no CDN dependencies, no restructure of the board.
- Also: don't add a linter/formatter, don't pin or add dependencies, and don't change application code when the task is a docs change.

Small, in-scope fixes to existing behavior are fine. Anything on this list — ask.

## Repository notes

- `tests/verify_a.py` is **not** a pytest file. It is a standalone script of print-based `PASS`/`FAIL` checks over the Pydantic models, run directly (`python tests/verify_a.py`). It defines no `test_*` functions, so pytest collects nothing from it.
- `.env` / `.env.example` (`PORT`, `APP_ENV`) and the `python-dotenv` dependency are unused — nothing in `app/` reads them. The port comes from the `uvicorn --port` flag.
- `app/` contains empty leftover scaffolding directories (`api/`, `core/`, `models/`, `storage/`). Note `app/models/` and `app/models.py` coexist, as do `app/storage/` and `app/storage.py`; the `.py` files are what import resolves to today, but adding an `__init__.py` to those directories would shadow the real modules.
- The virtual environment on disk is `.venv/`; `README.md` tells you to create `venv/`. `.venv/` is what exists and what the commands above assume.
- The `mid-course-project` branch is `main` plus 4 commits and adds a comments API, search/assignee filtering, an expanded frontend, and `docs/midcourse/` ADRs. **This file documents `main` only.** If you are working on that branch, the endpoint and model inventory above is incomplete.
