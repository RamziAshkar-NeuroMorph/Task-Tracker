# User Stories — Text Search & Filter Combinations

**Story:** As a team member, I want to filter tasks by priority.
**Acceptance Criteria:**
- Priority value must be from the accepted values, invalid value returns 422.

**Story:** As a team member, I want to search tasks by free-text keyword so that I can find a task without remembering its exact title.
**Acceptance Criteria:**
- Search matches against task title and description, case-insensitively.
- Partial word matches are returned (searching "depl" matches "Deploy API").
- An empty or whitespace-only search term returns the unfiltered task list rather than an error.
- A search term with no matches returns an empty list with 200, not 404.

**Story:** As a team member, I want to combine a text search with a status filter so that I can narrow results to work in a specific state.
**Acceptance Criteria:**
- When both `search` and `status` are supplied, only tasks satisfying both conditions are returned (AND, not OR).
- Status value must be one of the accepted values; an invalid value returns 422.
- Supplying only one of the two parameters applies that filter alone.

**Story:** As a team member, I want to filter tasks by assignee so that I can see the work belonging to one person.
**Acceptance Criteria:**
- Results include only tasks whose assignee matches the supplied value exactly.
- An assignee that matches no tasks returns an empty list with 200.
- Assignee may be combined with search, status, and priority in the same request.

**Story:** As a team member, I want to apply status, priority, and assignee filters together so that I can isolate a precise slice of the backlog.
**Acceptance Criteria:**
- All supplied filters are combined with AND; a task must satisfy every one to appear.
- Filters may be supplied in any order and any combination, including all three at once.
- Omitting all filters returns the full task list.
- Each supplied filter is validated independently; the response identifies which parameter failed validation.

**Story:** As a team member, I want invalid filter combinations to fail clearly so that I can correct my request instead of trusting wrong results.
**Acceptance Criteria:**
- An unrecognized query parameter name returns 422 rather than being silently ignored.
- A filter supplied with an empty value (e.g. `status=`) returns 422.
- When multiple parameters are invalid in one request, the error response lists all of them, not just the first.
- No partial results are returned alongside a validation error.

**AI assumption that I corrected**
- Case sensitive search matches.
