# Feature 1: Task Search and Filtering — Prompts

This document records the prompts I used while building Feature 1, along with the AI's output and the edits I made.

## Prompt 1 — Creating user stories

My new feature is to support text search and filter combinations such as status, priority, and assignee.

> Generate user stories for this feature in the same format and quality as this example.
>
> Example:
> Story: As a team member, I want to filter tasks by priority.
> Acceptance Criteria:
> - Priority value must be from the accepted values, invalid value returns 422.
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

**Result:** The AI returned the user stories found in [user-stories.md](user-stories.md). It made one wrong assumption about text search, which I edited.

## Prompt 2 — Adding search and filters to the frontend

**Weak prompt to change**
> Include this feature in the frontend.

**Updated prompt**
> Based on the updated @app/main.py, extend my existing task board to have search and filters included.
>
> Requirements:
> - Use vanilla HTML, CSS, and JavaScript only. No frameworks and no build step.
> - Add a search bar and filter inputs above the board.
> - Priority and status filters must be predefined.
> - Assignee and search filters are free text.
>
> Output:
> - Add the code to @frontend/index.html, keep it readable.

**Result:** The AI updated the index.html file with a summary of the changes applied (location and what changed). It returned a filters bar with all the needed inputs.

**Follow-up:** API calls were made on every input for the text and assignee search, so I asked the AI to add a debounce delay before it calls the API.

## Prompt 3 — Fixed header and scrollable columns

With a lot of tasks, the user had to scroll through the whole page.

> Task:
> - Keep the app header, filters bar, and column headers fixed on scroll.
> - Make every column scrollable on its own.

**Result:** The AI updated the HTML code. I reviewed and tested the changes, then accepted them.
