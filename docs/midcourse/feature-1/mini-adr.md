# ADR-001: Text Search and Filter Combinations on `GET /tasks`

- **Status:** Accepted
- **Date:** 2026-07-21
- **Related files:** [app/main.py](../../../app/main.py), [app/storage.py](../../../app/storage.py), [app/models.py](../../../app/models.py), [frontend/index.html](../../../frontend/index.html)

## Decision

I added two features to `GET /tasks`: free-text **search** and **filter combinations**
(status, priority, assignee, all combinable in one request).

### How I implemented text search

- A `search` query parameter that does a case-insensitive substring match over `title`
  and `description`. Both sides are lower-cased before comparison, so `deploy` matches
  `Deploy API`, and partial words match.
- A whitespace-only `search` is treated as absent, not as an error. No matches returns
  200 with an empty list, not 404.

### How I implemented filter combinations

- `status`, `priority`, `assignee`, and `search` are optional parameters on `list_tasks`,
  applied as successive filter steps in `storage.get_all_tasks`. All supplied filters
  combine with AND; omitted ones are skipped, so no filters returns the full list.
- The parameters are grouped into a `TaskFilters` Pydantic model with `extra="forbid"`,
  matching the pattern already used by `TaskCreate` / `TaskUpdate`. An unknown parameter
  like `?statuss=Done` now returns 422 instead of silently returning unfiltered results.
- `status` and `priority` keep their existing enum validation, so invalid values return
  422 through FastAPI with no hand-written checks.
- On the frontend, a filter bar above the board sends these parameters to the API. Text
  inputs are debounced so typing doesn't fire a request per keystroke.

## Alternatives the AI suggested

- **Fuzzy or ranked matching** for search instead of plain substring matching.
- **Moving storage to SQLite** so filtering could push down into real queries with
  indexes and LIKE.
- **Returning 404 when no tasks match** a search.
- **Case-sensitive search** — this was the AI's initial assumption, which I corrected
  (the user stories require case-insensitive matching).

## What I rejected and why

- **Fuzzy matching — too complex.** Substring matching satisfies every acceptance
  criterion, and relevance ranking is a different feature.
- **SQLite migration — out of scope.** Storage is an in-memory dict with small task
  volume; a linear scan is fine at this scale. If storage ever moves to a database,
  filtering should be revisited there.
- **404 on empty results — rejected as wrong semantics.** An empty result set is a
  valid answer, not a missing resource.
- **Pagination and sorting options — out of scope.** Not part of the stories; the board
  already orders cards client-side.

## Trade-off I accepted

Rejecting unknown parameters is technically a breaking change for any client sending
stray query strings (they now get 422 instead of a silently unfiltered 200). The only
consumer is [frontend/index.html](../../../frontend/index.html), which I updated in the
same change, so I accepted this to turn a silent wrong-results bug into a loud error.
See [verification.md](../verification.md) for the before/after behavior table and test
evidence, and [user-stories.md](user-stories.md) for the acceptance criteria.
