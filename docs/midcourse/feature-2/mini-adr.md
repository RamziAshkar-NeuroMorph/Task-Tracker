# ADR-002: Task Comments

- **Status:** Proposed
- **Date:** 2026-07-23
- **Related files:** [app/main.py](../../../app/main.py), [app/storage.py](../../../app/storage.py), [app/models.py](../../../app/models.py)
- **User stories:** [user-stories.md](user-stories.md)

## Decision

Add comments to tasks as a sub-resource of the existing task API, following the
patterns already established in the codebase

### Data model

A `Comment` has:

- `id` — server-generated UUID string, same as tasks.
- `task_id` — the owning task's id.
- `text` — required, stripped, non-blank, max 1000 characters.
- `created_at` — server-set UTC timestamp, never changed after creation.
- `edited_at` — `None` until the comment is first edited; overwritten with the
  server time on every subsequent edit (only the **last** edit time is kept, per
  the user stories).

Comments are **not** embedded in `TaskResponse`. The task response shape stays
unchanged, and comments are fetched through their own endpoints.

### Endpoints

Comments are nested under their task, so the task-existence check is uniform:

- `POST /tasks/{task_id}/comments` — create, returns 201 with the comment.
- `GET /tasks/{task_id}/comments` — list, ordered by `created_at` oldest first.
  Empty list with 200 when the task has no comments.
- `PATCH /tasks/{task_id}/comments/{comment_id}` — edit the text, sets `edited_at`.
- `DELETE /tasks/{task_id}/comments/{comment_id}` — delete, returns 204.

Any operation against a non-existent `task_id` or `comment_id` returns 404, and
a failed create/edit never persists anything (no partial writes).

### Storage

A second in-memory dict in [app/storage.py](../../../app/storage.py), keyed by
task id: `_comments: dict[str, list[CommentResponse]]`. Appending preserves
creation order, so the "oldest first" criterion falls out of the data structure
with no sorting. Edit/delete does a linear scan of the task's list by comment
id — fine at this scale, same reasoning as the filter scans in ADR-001.

Deleting a task also deletes its comments, so no orphaned comments can accumulate.

### Validation

- `CommentCreate` / `CommentUpdate` models with `extra="forbid"` and a `text`
  validator mirroring the existing title validator (strip, reject blank, enforce
  the 1000-character limit with the limit named in the error message).
- Timestamps are never accepted from the client; they exist only on the response
  model, so the server is the sole source of `created_at` / `edited_at`.

## Alternatives the AI suggested

- **Embedding comments inside the task object** so `GET /tasks` returns them inline.
- **Keeping a full edit history** (list of revisions) rather than a single
  `edited_at` timestamp.
- **Soft-deleting comments** (a `deleted` flag) instead of removing them.

## What I rejected and why

- **Embedded comments — rejected.** It changes the shape of every existing task
  response, bloats the board's list payload with data the board doesn't show, and
  would ripple through `TaskResponse`, the filters, and existing tests. A separate
  endpoint keeps this feature additive.
- **Full edit history — out of scope.** The user stories (including the edit I
  suggested) explicitly ask for only the last edit time. Revisions are a
  different feature.
- **Soft delete — rejected.** Nothing in the stories needs undelete or audit, and
  tasks themselves hard-delete; comments should behave consistently.

## Trade-off I accepted

The user stories say a client-supplied timestamp should be **ignored**, but the
codebase convention is `extra="forbid"`, which returns **422** for any unknown
field — including a stray `created_at` in the body. I chose consistency with the
convention (and with ADR-001's "loud error over silent surprise" reasoning):
a client sending timestamps gets 422 rather than silent acceptance-by-ignoring.
The acceptance criterion in [user-stories.md](user-stories.md) should be read as
"the server never trusts a client timestamp", which 422 satisfies more strictly.
