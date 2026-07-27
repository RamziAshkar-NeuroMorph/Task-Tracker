# Technical Decision Note — Status Transition Rules

**Status:** Final — describes the implementation on `main`
**Project:** Module 4 Task Tracker (`main` branch)
**Scope:** `app/business_rules.py`, the PATCH path in `app/main.py`, `TaskStatus` in `app/models.py`, and the drag-and-drop behaviour in `frontend/index.html`
**Date:** 2026-07-27

---

## 1. Context

A task moves across a three-column Kanban board: `ToDo` → `InProgress` → `Done`. Without a rule, `PATCH /tasks/{id}` would accept any status change at all — a task could jump straight from `ToDo` to `Done`, or slide backwards from `Done` to `ToDo`, and the board would silently record work that never happened.

The module brief calls for a *state machine*: not every status change is permitted. That raises four separate questions, and this note records how each was answered:

1. **Which moves are legal?**
2. **Where does the rule live** — model, route, storage, or its own module?
3. **When is it checked** — on create, on update, or both?
4. **What does an illegal move return** to the client, and what does the client do with it?

The surrounding constraints matter. Storage is a module-level dict in `app/storage.py` with no persistence, no transaction, and no history — there is no audit trail to reconstruct how a task reached its current status, so the *current* status is the only input the rule can use. The project layering is deliberate and narrow: `storage.py` signals absence by return value and never raises HTTP errors; `main.py` owns every `HTTPException` for 404s. There is no auth, so there is no notion of "who" is allowed to move a task — only "what" moves are allowed. And the frontend is a drag-and-drop board, which means every rule decided here is a rule a user will hit by dragging a card three pixels too far.

## 2. Decision

Model the rule as an **explicit allowlist of `(from, to)` pairs**, held in `VALID_TRANSITIONS` in a dedicated `app/business_rules.py`, and enforce it on `PATCH` only.

Concretely:

- **`VALID_TRANSITIONS` is a `frozenset[tuple[TaskStatus, TaskStatus]]` containing exactly six pairs.** Membership *is* the rule — `validate_status_transition()` is a single `in` check with no branching logic, so the table is the complete specification and reading the file tells you the whole behaviour.

  | from ↓ / to → | ToDo | InProgress | Done |
  | --- | --- | --- | --- |
  | **ToDo** | allowed | allowed | rejected |
  | **InProgress** | rejected | allowed | allowed |
  | **Done** | rejected | allowed | allowed |

- **`ToDo → Done` is rejected.** Work passes through `InProgress`; you cannot mark something finished that was never started.
- **`Done → InProgress` is allowed.** Reopening a task is a real workflow and the state machine supports it.
- **Nothing returns to `ToDo` once it has left.** Both `InProgress → ToDo` and `Done → ToDo` are rejected.
- **The three self-transitions are listed explicitly.** Re-sending a task's current status returns 200, which makes a status PATCH idempotent and means a drag that lands a card back in its own column is not an error.
- **The rule lives in its own module**, not in the models and not in the route. `app/models.py` defines the `TaskStatus` enum and nothing about how statuses relate; `business_rules.py` owns the relation.
- **Enforcement happens in `app/main.py:196-200`, before the write.** The handler re-fetches the task to learn its current status, validates the transition, and only then calls `storage.update_task`. `storage.py` knows nothing about transitions.
- **Order is fixed: 404 before 422.** An unknown `task_id` is a 404 even when the requested transition would also have been illegal. This is why the existence check appears twice in `update_task`.
- **An illegal move returns 422** with a detail that names both statuses and enumerates every allowed pair: `"Invalid status transition from ToDo to Done. Allowed transitions: ['Done->Done', 'Done->InProgress', 'InProgress->Done', 'InProgress->InProgress', 'ToDo->InProgress', 'ToDo->ToDo']"`.
- **The frontend does not duplicate the table.** It performs the PATCH, and `showBoardNotice()` surfaces the server's 422 detail above the board. The server is the single source of truth.

`POST /tasks` accepts any of the three statuses directly and consults no table — creation is an entry point into the machine, not a move within it.

## 3. Alternatives Considered

**A. No transition rules; any status change permitted.** Simplest possible API, and every PATCH becomes a plain field update. Rejected because the state machine is the point of the exercise, and because a board with no rules cannot distinguish a workflow from a set of arbitrary labels.

**B. A `dict[TaskStatus, set[TaskStatus]]` adjacency map** instead of a flat set of pairs. Reads slightly more naturally (`VALID_TRANSITIONS[current]`) and makes "what can this task do next?" answerable in one lookup — useful if the frontend ever wants to grey out illegal drop targets. Rejected for now because the flat frozenset keeps `validate_status_transition` to a single membership test with no `KeyError` case to handle, and because the six pairs fit on one screen. This is the alternative most likely to be revisited.

**C. A third-party state-machine library** (e.g. `transitions`). Rejected: it adds a dependency to a project whose whole rule set is six tuples, and dependencies are on the "ask first" list.

**D. Enforce the rule inside `app/models.py`, as a Pydantic validator on `TaskUpdate`.** Rejected because it is not expressible there — a field validator sees only the incoming value, and the rule needs the task's *stored* status, which the model has no access to. This constraint, more than any preference, is what forced the rule into a layer that can read storage.

**E. Enforce the rule inside `app/storage.py`, next to the write.** Tempting: it would remove the double fetch and the double 404 check, and would make the rule impossible to bypass by calling storage directly. Rejected because it breaks the project's layering contract — `storage.py` returns `None`/`False` and never raises HTTP errors — and because it would put a 422 concern inside the one module that is supposed to be transport-agnostic.

**F. Return `409 Conflict` rather than `422`.** Arguably more correct: the request body is well-formed and individually valid, and what fails is its compatibility with current server state, which is what 409 describes. Rejected for consistency — every other rejection in this API (blank title, unknown field, bad enum value) is a 422, and a single endpoint returning two different 4xx codes for two flavours of "no" is harder for the frontend to handle than one code with a readable detail. If the course brief turns out to mandate a specific code for this case, that overrides the consistency argument.

**G. Omit the self-transitions, making `ToDo → ToDo` a 422.** Rejected: a PATCH that re-sends the current status is a no-op, not an error, and rejecting it would make the endpoint non-idempotent for no gain. It would also make the drag-and-drop board fail on a card dropped back into the column it came from.

**H. Apply the same table to `POST /tasks`,** so tasks could only ever be created in `ToDo`. Rejected — creation has no "from" status, so the table does not apply. The consequence is noted honestly below rather than papered over.

**I. Enforce the rules in the frontend and let the API accept anything.** Rejected outright. The API is directly reachable at `/docs` and by `curl`; a rule enforced only in the browser is not a rule.

## 4. Trade-offs

- **The rules govern `PATCH` and nothing else, so `POST` is an open door.** `create_task` copies `payload.status` straight through, so `POST /tasks {"status": "Done"}` creates a finished task that never passed through `InProgress` — exactly the sequence the table exists to prevent. I rely on this myself: `tests/test_tasks.py:126-130` uses it to set up a `Done` task for the `Done → ToDo` rejection test. The state machine I built constrains movement, not entry, and the `create_task` docstring says so outright. Whether that is a considered design or an unclosed gap is the first open question below.
- **`PATCH {"status": null}` bypasses validation entirely and corrupts the record.** The guard is `if payload.status is not None`, so an explicit null skips the check, reaches `model_copy(update=...)` — which does not re-validate in Pydantic v2 — and writes `status: null` onto the stored task. The request returns 200 and the null persists, served on every subsequent GET. This is a defect, not a rule, and it means the invariant "every stored task has one of three statuses" is not actually enforced by anything. It is recorded as an open defect in `README.md` and `CLAUDE.md`, and it should not be described as behaviour.
- **`business_rules.py` imports `fastapi` and raises `HTTPException` directly.** This is the mirror image of the layering discipline I applied to `storage.py`, and the inconsistency is worth naming: storage is transport-agnostic, business rules are not. It keeps the call site in `main.py` to two lines, but it means the rule cannot be reused by any non-HTTP caller, and a unit test of `validate_status_transition` has to assert on an HTTP exception rather than a domain error.
- **Validating before writing costs a second lookup.** `main.py` fetches the task to read its current status, then `storage.update_task` fetches it again — and both need their own `None` check, which is why the 404 raise appears twice in one handler. That duplication is the visible price of keeping storage ignorant of the rules. The route handlers are plain `def`, so FastAPI runs them in a threadpool: the check-then-write sequence is not atomic, and two concurrent PATCHes on the same task could in principle interleave between validation and write. With an in-memory dict and a single course user that is theoretical, but it is a check-then-act race and I will not describe it as safe.
- **The 422 detail enumerates the entire transition table on every rejection.** Genuinely helpful — the client is told not just that it was wrong but what would have been right, without a separate documentation lookup. The costs: the message is long, it is rebuilt by `sorted()` on every failure rather than computed once at import, and it is a raw Python list repr (`['Done->Done', ...]`) leaking into a JSON string, which is awkward for a frontend that wants to render the options rather than print them. The board currently just displays the whole string in a notice.
- **The frontend lets users attempt moves that will certainly fail.** Because the board does not duplicate the table, a card can be dragged from `ToDo` to `Done` and only then rejected. Single source of truth is the right call, but the interaction cost is real. The drop handler applies the new status optimistically, re-renders, then PATCHes; on a non-2xx response it restores the previous task object locally and calls `showBoardNotice()` with the server's detail. So the card does snap back, but the board never re-reads the server — the revert is a local guess that happens to be correct today only because the rejected PATCH wrote nothing.
- **"Nothing returns to `ToDo`" is a strong, opinionated rule with no escape hatch.** A task started by mistake cannot be un-started. With no auth, no roles, and no admin path, the only remedy is DELETE and re-create — which loses the `id` and `created_at`. I am not certain that severity was intended rather than a side effect of leaving two pairs out of the table.
- **Six explicit pairs do not scale, but the project does not need them to.** Adding a fourth status turns 6 pairs into as many as 16 decisions, and the flat set gives no help enumerating what is missing. At three statuses this is a feature: the table is exhaustive and auditable at a glance.
- **The suite covers four transition cases**, not the full matrix: `ToDo → InProgress` (200), `ToDo → Done` (422), `ToDo → ToDo` (200), and `Done → ToDo` (422, with the detail asserted). `InProgress → ToDo`, `Done → InProgress`, `InProgress → Done`, and the `InProgress`/`Done` self-transitions are not exercised, so parts of the table I document here are asserted only by my having read the file.
- **`HTTP_422_UNPROCESSABLE_ENTITY` is deprecated** in favour of `HTTP_422_UNPROCESSABLE_CONTENT`, and the suite emits a warning for it. The wire behaviour is unchanged — still 422 — but the constant used at `app/business_rules.py:41` is on an upstream rename path.

## 5. Consequences

**Immediate**

- The complete rule set is one 12-line literal. A reviewer confirms the behaviour by reading `VALID_TRANSITIONS`, not by tracing conditionals.
- Changing the workflow means editing the table and nothing else — no route change, no model change, no frontend change. The 422 message updates itself, since it is generated from the table.
- Clients receive a self-describing rejection: what they tried, and what is permitted.
- A nonexistent task always yields 404, never 422, so clients can distinguish "no such task" from "not allowed" without parsing the detail string.
- `main.py` carries a duplicated existence check that only exists because of the pre-write validation, and any future change to the PATCH path has to keep both branches consistent.

**Downstream / follow-on**

- Adding a status (`Blocked`, `InReview`) requires deciding every new pair deliberately, in one place. That is the intended cost.
- If the frontend later wants to grey out illegal drop targets, it needs the allowed set per status — which argues for exposing the table (an endpoint, or the adjacency-map form from alternative B) rather than having the board hardcode a second copy that can drift.
- The `{"status": null}` defect means any future code that assumes a stored task has a valid `TaskStatus` is building on an invariant the API does not currently guarantee. Fixing the guard is a prerequisite for relying on it.
- Because the store is in-memory with no history, no rule that depends on a task's *past* — "cannot reopen after 24h", "cannot skip stages twice" — is expressible without adding state to `storage.py` first.

**Explicitly not consequences.** These rules are not permissions: there is no auth, no roles, and no notion of who may move a task — only which moves exist. They are not database constraints; nothing at the storage layer enforces them, and a direct call to `storage.update_task` bypasses them completely. And they are not enforced across restarts, because there is nothing to restart into — the store is empty every time the process starts.

## 6. Open Questions

1. Should `POST /tasks` be restricted to creating tasks in `ToDo`, or is creating directly in `InProgress`/`Done` intended (seeding, importing)? Tightening it means reworking the setup in `test_patch_done_to_todo_returns_422_with_invalid_transition_detail`, which is the one test that depends on the permissive behaviour.
2. When is the `{"status": null}` bypass being fixed, and how — reject an explicit null as a 422, or treat it as "no change"? `CLAUDE.md` says to ask before changing it, so this needs a decision before any code moves.
3. Should `validate_status_transition` raise a domain exception (`InvalidTransitionError`) that `main.py` translates into a 422, so that `business_rules.py` stops importing FastAPI and matches the discipline already applied to `storage.py`?
4. Is `422` the right code, or should an illegal transition be `409 Conflict`? Does the module brief specify one?
5. Should `VALID_TRANSITIONS` become a `dict[TaskStatus, set[TaskStatus]]` so a "what can this task do next?" lookup is possible — and should that be exposed to the frontend so illegal drags are prevented rather than rejected?
6. Should the 422 detail return a structured field (a JSON array of allowed transitions) instead of a Python list repr embedded in a sentence, so the frontend can render options rather than print a string?
7. Should the transition table be tested exhaustively — all nine `(from, to)` pairs, parametrized — rather than the four cases currently covered?
8. Is "nothing may return to `ToDo`" the intended severity? If a task is started by mistake, the only correction available is delete-and-recreate, which loses the `id` and `created_at`.
9. Should the allowed-transitions string be computed once at import instead of re-sorted on every rejection? Trivial, but it is currently rebuilt on each failed request.
10. After a rejected drag the board reverts the card from a locally cached copy rather than re-reading the API. Should it re-fetch instead, so the UI is showing state the server confirmed rather than state it inferred?
11. Should `HTTP_422_UNPROCESSABLE_ENTITY` be swapped for `HTTP_422_UNPROCESSABLE_CONTENT` now to clear the deprecation warning, or left until the upstream rename forces it?

## 7. I would do this differently by...

**I would do this differently by** validating the transition where the write happens, instead of ahead of it in the route.

The thing I keep returning to is that I built a rule to protect an invariant, and then left two ways around it. `POST` lets me create a `Done` task that never touched `InProgress` — I even lean on that in my own tests to set up a fixture — and `PATCH {"status": null}` walks straight past the check and writes a null into the store. If someone asked me "can a task in this system be in an invalid state?", the honest answer today is yes, twice over. The table isn't wrong; it just isn't the only path to the field it governs.

What caused that, I think, is that I put the check in the route because the route was where I happened to have both the old and new status in hand. That's a convenience, not a design. Validating on the way *in* to the write — one place every status change has to pass through — would have closed both holes for free, because there'd be no second door to forget about. I talked myself out of it at the time by pointing at the layering rule, but the layering rule is really about `storage.py` not raising `HTTPException`, and I broke the spirit of that anyway by importing FastAPI into `business_rules.py`. If I were redoing it, I'd have the rule raise a plain domain error and let `main.py` be the only module that knows what a 422 is. Then it genuinely wouldn't matter which layer called it.

Two smaller things I'd change. I'd write the table as `dict[TaskStatus, set[TaskStatus]]` rather than a flat set of pairs — not because the current form is unclear at three statuses, but because the adjacency form answers "what can this card do next?", and that's the question the board actually needs to stop offering drops it knows will fail. And I'd parametrize the tests over all nine combinations instead of hand-picking four; the table is small enough that exhaustive is cheaper to write than selective, and right now half of the rules I document here are asserted only by my having read the file.

What I'd keep: the six pairs as data rather than `if` statements, self-transitions being explicitly legal, 404 winning over 422, and the error message telling the client what *would* have worked. Those all still look right to me.
