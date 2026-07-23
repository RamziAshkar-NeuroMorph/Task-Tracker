# User Stories — Task Comments

**Story:** As a team member, I want to add a comment to a task.
**Acceptance Criteria:**
- Comment must be non-blank text.

**Story:** As a team member, I want to view all comments on a task so that I can follow the discussion about that work item.
**Acceptance Criteria:**
- Comments are returned as a list scoped to the requested task ID.
- Comments are ordered by creation time, oldest first.
- A task with no comments returns an empty list with 200, not 404.
- Requesting comments for a non-existent task ID returns 404.

**Story:** As a team member, I want each comment to record when it was created so that I can understand the timeline of a discussion.
**Acceptance Criteria:**
- Every comment includes a creation timestamp set by the server, not supplied by the client.
- The timestamp is returned in a consistent ISO 8601 format.
- A client-supplied timestamp in the request body is ignored rather than causing an error.

**Story:** As a team member, I want to edit a comment I previously added so that I can correct mistakes or clarify what I wrote.
**Acceptance Criteria:**
- Editing replaces the comment text; the edited text must be non-blank.
- Editing a comment on a non-existent task or a non-existent comment ID returns 404.
- The comment's creation timestamp is unchanged by an edit.
- An edited comment records an edited timestamp, set by the server; only the most recent edit time is kept.
- A comment that has never been edited has no edited timestamp.

**Story:** As a team member, I want to delete a comment so that I can remove content that is no longer relevant.
**Acceptance Criteria:**
- A deleted comment no longer appears in the task's comment list.
- Deleting a non-existent comment ID returns 404.
- Deleting a comment does not affect the task itself or other comments on it.

**Story:** As a team member, I want invalid comment submissions to fail clearly so that I can correct my request instead of creating bad data.
**Acceptance Criteria:**
- A comment with empty or whitespace-only text returns 422.
- A comment exceeding the maximum allowed length (e.g. 1000 characters) returns 422 with a message stating the limit.
- Submitting a comment to a non-existent task ID returns 404 and no comment is created.
- A request body missing the text field entirely returns 422, not a blank comment.

**Edit I suggested to the AI**
- Edited comments should record an edited timestamp, keeping only the last edit time.
