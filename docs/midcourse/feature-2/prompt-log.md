# Feature 2: Task Comments — Prompts

This document records the prompts I used while building Feature 2, along with the AI's output and the edits I made.

## Prompt 1 — Creating user stories

My new feature is to support Task comments.

> Generate user stories for this feature in the same format and quality as this example.
>
> Example:
> Story: As a team member, I want to add a comment to a task.
> Acceptance Criteria:
> - Comment must be non-blank text.
>
> Now generate five more stories in the same format.
>
> Constraints:
> - Use "team member" as the user role.
> - Do not mention login, authentication, user accounts, admin roles, notifications, mobile, or real-time updates.
> - Include at least one failure case across the generated stories.
>
> Output format:
> Return each story with Story and Acceptance Criteria headings.

**Result:** The AI returned the user stories found in [user-stories.md](user-stories.md).

**Edit I suggested:** Edited comments should record an edited timestamp, keeping only the last edit time. The AI added this to the edit story's acceptance criteria.


## Prompt 2 — Backend Implementation

**Weak prompt to change**
> Include this feature in the frontend.

**Updated prompt**
> Based on @docs/midcourse/feature-2/user-stories.md and the decisions in @docs/midcourse/feature-2/mini-adr.md, implement the Task Comments feature. Follow the conventions already used in @app/models.py, @app/storage.py, and @app/main.py.
>
> Requirements:
> - Add CommentCreate, CommentUpdate, and CommentResponse models. Comment text is required, trimmed, non-blank, max 1000 characters. Reuse the same validator style as the task title.
> - Timestamps are set by the server only. edited_at stays null until the first edit and always keeps just the last edit time.
> - Store comments in a new in-memory dict keyed by task id, ordered oldest first. Deleting a task should delete its comments too. Don't forget _reset().
> - Endpoints: POST, GET, PATCH, DELETE under /tasks/{task_id}/comments as decided in the ADR. 404 for any missing task or comment id.
> - Write tests for every acceptance criterion in the user stories, including the failure cases (blank text, too long text, missing text field, unknown fields, missing ids, cascade on task delete).
>
> Constraints:
> - Do not change TaskResponse or any existing endpoint behavior.
> - API and tests only, no frontend changes yet.
> - No new dependencies and no database.
> - Run the whole test suite at the end and show me the results. Existing tests must still pass.

**Result:**
 The AI implemented the feature across [app/models.py](../../../app/models.py) (three comment models mirroring the task validator style), [app/storage.py](../../../app/storage.py) (a per-task comment dict with cascade delete and `_reset()` coverage), and [app/main.py](../../../app/main.py) (the four nested endpoints with a shared task-existence check). It added 23 tests in [tests/test_comments.py](../../../tests/test_comments.py) covering every acceptance criterion, including failure cases and a boundary test at exactly 1000 characters.

## Prompt 3 — Frontend Implementation

> Based on the updated @app/main.py, @app/models.py  and @app/storage.py  extend my existing task board to allow user to add/view/edit/delete comments

> Requirements:
> - Use vanilla HTML, CSS, and JavaScript only. No frameworks and no build step.
> - Add a comment input in add/edit task dialog.
> - Make sure comment validations are present in frontend also.
> - No comments found shows an empty state.
>- If comment is edited, 'Edited' date is the date to show beside comment
>
> Output:
> - Add the code to @frontend/index.html, keep it readable.
**Result:** The AI updated the index.html file with a summary of the changes applied (location and what changed). It returned a comments section and a textarea. Although, styling was so messy.

**Follow-up:** Asked the AI to fix comments section styling.
