# Verification — Mid-course Project

- **Date:** 2026-07-23
- **Branch:** `mid-course-project` (at commit `12d6039`)
- **Related files:** [app/main.py](../../app/main.py), [app/storage.py](../../app/storage.py),
  [app/business_rules.py](../../app/business_rules.py), [frontend/index.html](../../frontend/index.html),
  [tests/test_tasks.py](../../tests/test_tasks.py), [tests/test_comments.py](../../tests/test_comments.py)

This document records the verification I did **before** starting the frontend refactor:
a baseline check, the backend test results, manual browser checks against the running app,
the behavior contract I will re-run after the refactor, and break-test evidence proving
the tests actually catch regressions.

## 1. Baseline check

Before touching anything I confirmed the app runs end to end:

- Backend up via uvicorn on `http://localhost:8000`; `GET /health` returns
  `{"status": "ok", "timestamp": "..."}`.
- Frontend served on `http://localhost:5500` (allowed origin in the CORS config),
  board loads and renders tasks from the API.
- Full test suite green on the working tree:

```
$ python -m pytest -q
51 passed, 3 warnings in 0.93s
```

The 3 warnings are Starlette/httpx deprecation notices, not failures. This is the
baseline every later change gets compared against: **51 passing tests, working board.**

## 2. Backend test results

| Test file | Tests | Result |
|---|---|---|
| [tests/test_tasks.py](../../tests/test_tasks.py) — CRUD, filters, search, status transitions | 28 | all pass |
| [tests/test_comments.py](../../tests/test_comments.py) — comment CRUD, validation, 404s | 23 | all pass |
| **Total** | **51** | **51 passed in ~1s** |

## 3. Manual browser checks

I opened the board in the browser (frontend on `:5500`, backend on `:8000`) with the Network tab open to watch the requests. I created a few
throwaway tasks with a `[BC]` title prefix for the checks and deleted them afterwards.

- The board renders three columns (To Do / In Progress / Done) and the count badges
  match what `GET /tasks` returns. Columns that end up empty stay on the board with a
  count of 0 and a "No tasks in this column yet." placeholder.
- While tasks are still being fetched, the "Loading tasks…" card shows first and is
  replaced by the columns once the response arrives.
- When the API is unreachable, the "Unable to load tasks" overlay appears with a Retry
  button, and Retry brings the board back once the API is reachable again.
- Dragging a card from To Do to In Progress fires a single `PATCH /tasks/{id}` with
  body `{"status":"InProgress"}` (checked in the Network tab), the card lands in the
  new column, both counts update, and the change is still there after a reload.
- Dragging a Done card back to To Do gets a real 422 from the backend; the exact
  server message ("Invalid status transition from Done to ToDo…") shows in the banner
  and the card snaps back to Done. The API state stays unchanged.
- The filter bar sits above the board. Each filter works on its own, and combining
  three at once (`/tasks?search=low&status=ToDo&assignee=Ramzi`) returned exactly
  the one task matching all of them. Clear restores the full board.
- New Task and Edit modals work end to end: a whitespace-only title is rejected with
  "Title is required" and no request is sent; Esc, Cancel, and clicking the backdrop
  all close the modal without saving. A comment typed while creating a task is posted
  right after the task is saved and shows up in the Edit modal, where I could edit it
  (gets an "Edited" timestamp), delete it, and see the "No comments yet." empty state
  once the last one was gone.
- The console stayed clean during all of this apart from the errors the two failure
  scenarios are supposed to produce (connection refused, 422).

## 4. Behavior contract — before/after refactor

The contract the refactor must preserve. "Before" was verified on 2026-07-23. The
refactor extracted the backend origin into a single `API_BASE_URL` constant in
[frontend/index.html](../../frontend/index.html) and
"After" was verified on 2026-07-24 by re-running the same checks. All 8 still pass.

| ID | Behavior | Before refactor | After refactor |
|----|----------|-----------------|----------------|
| BC-1 | Three status columns render with counts matching the API; empty columns stay visible with a count of 0 and a placeholder | PASS — ToDo=3 / InProgress=1 / Done=1 matched; 2 emptied columns kept placeholders | PASS — counts still match the API; 2 emptied columns kept placeholders |
| BC-2 | Cards sort by priority (High → Medium → Low) inside each column regardless of creation order | PASS — created High, Low, Medium; rendered High > Medium > Low | PASS — rendered High > Medium > Low |
| BC-3 | Loading state shows between page open and first successful `GET /tasks`, then disappears | PASS — "Loading tasks…" shown during slowed fetch, gone after load | PASS — "Loading tasks…" shown while the fetch was held open, gone once it resolved |
| BC-4 | Error state (message + Retry) when the backend is unreachable; Retry recovers once it's back | PASS — overlay shown, Retry reloaded the board | PASS — overlay shown, Retry reloaded the board once reachable |
| BC-5 | Valid drag sends one `PATCH /tasks/{id}` with the new status; card, counts, and persisted state all update | PASS — body `{"status":"InProgress"}` captured; API confirms persistence | PASS — same `PATCH /tasks/{id}` with `{"status":"InProgress"}`; persisted |
| BC-6 | Invalid drag (real 422) reverts the card and surfaces the server's `detail` message | PASS — exact transition-rule message shown in banner; card back in Done; API unchanged | PASS — server message in banner; card back in Done; API unchanged |
| BC-7 | Filter bar renders above the board; search/status/priority/assignee all work and combine with AND | PASS — combined query returned exactly the one matching task | PASS — `search=low&status=ToDo&assignee=...` returned exactly the one matching task |
| BC-8 | New Task / Edit modals work: title validation (no request on invalid title), Esc/Cancel/backdrop dismissal, comments list + edit + delete + empty state | PASS — all 15 sub-checks | PASS — all 15 sub-checks |

## 5. Break-test evidence

To prove the suite isn't vacuously green, I deliberately broke the code in two places,
confirmed the tests fail for the right reason, and reverted. Suite was back to
`51 passed` after each revert.

### Break 1 — remove case-insensitive matching from search

In [app/storage.py](../../app/storage.py), `get_all_tasks`:

```python
# before (correct)
if needle in task.title.lower() or needle in task.description.lower()
# broken
if needle in task.title or needle in task.description
```

Result: **3 failures**, exactly the tests that guard this behavior:

```
FAILED tests/test_tasks.py::test_list_tasks_search_matches_title_case_insensitively
FAILED tests/test_tasks.py::test_list_tasks_search_matches_partial_word_and_description
FAILED tests/test_tasks.py::test_list_tasks_combined_filters_apply_as_and
3 failed, 48 passed

>       assert len(tasks) == 1
E       assert 0 == 1
E        +  where 0 = len([])
```

Searching `deploy` no longer matched `Deploy API`, which is precisely the acceptance
criterion from [feature-1/user-stories.md](feature-1/user-stories.md).

### Break 2 — disable the status-transition rule

In [app/business_rules.py](../../app/business_rules.py), `validate_status_transition`:

```python
# broken: guard can never fire
if False and (current, new) not in VALID_TRANSITIONS:
```

Result: **2 failures**, the transition tests:

```
FAILED tests/test_tasks.py::test_patch_invalid_transition_todo_to_done_returns_422
FAILED tests/test_tasks.py::test_patch_done_to_todo_returns_422_with_invalid_transition_detail
2 failed, 49 passed

>       assert response.status_code == 422
E       assert 200 == 422
E        +  where 200 = <Response [200 OK]>.status_code
```

An illegal ToDo → Done jump started returning 200, and the tests caught it.

### A mutation that survived (gap found)

Not everything I broke was caught. Removing `.lower()` from the **search term** only
(`needle = search` instead of `needle = search.lower()`, haystack still lower-cased)
left all 51 tests green. The case-insensitivity test searches with a lowercase term
(`"deploy"`), so it never exercises an uppercase query like `"DEPLOY"`.

**Follow-up:** add a test that searches with an uppercase/mixed-case term before
relying on the suite during the refactor.
