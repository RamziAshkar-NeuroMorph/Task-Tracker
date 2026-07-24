# Reflection — Working with AI

For this project I used Claude Code as my main AI assistant, alongside the inline
suggestions in my editor. I leaned on it for a few distinct jobs rather than one big
"write my app" prompt. It created my user stories, prepared a draft plan for backend
implementation and generated both frontend and backend code additions. It also laid out
the eight-item behavior contract I used to check the board, and did the refactor
(pulling the backend origin into a single `API_BASE_URL` constant). For anything touching
the actual contract — the status values, the priority order, the optimistic-update
rollback — I kept the AI on a short leash with explicit "do not change" constraints.

The moment it clearly helped was the verification pass. Having the AI write the contract
out as an explicit before/after checklist meant that when I went through the eight
behaviors by hand — stopping the backend to see the error state, confirming the right
`PATCH` body went out, checking the comment empty state — I had a fixed list to follow
instead of improvising. After the refactor I could walk the exact same checks and trust
the "before/after" table, rather than skipping steps out of boredom and hand-waving it.

The moment it slowed me down was setup noise. An `npm install` for the browser driver
misfired into my project root and left a stray `package.json`, `package-lock.json`, and
`node_modules` that had nothing to do with my Python app. I had to notice it, confirm
those files weren't tracked, and clean them out before they polluted the repo.

The place my own review changed the result was the break tests. When I deliberately broke
search to prove my tests catch regressions, my first attempt — removing `.lower()` from
only the search term — left all 51 tests green. If I'd trusted the "green means safe"
story, I'd have missed it. Reading why it survived showed a real gap: my case-insensitivity
test only ever searches with a lowercase term, so an uppercase query is never exercised. I
wrote that down as a follow-up. The AI generated the mutation; noticing what its silence
meant was on me.

