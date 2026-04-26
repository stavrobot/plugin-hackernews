---
id: ph-ookcv
status: open
deps: []
links: []
created: 2026-04-26T13:49:03Z
type: task
priority: 2
assignee: Stavros Korokithakis
---
# Add submit_story tool

Add a new tool that submits a story to Hacker News using the user's HN `user` cookie.

Tool: submit_story/ (Python, uv shebang, deps: requests, beautifulsoup4).

Parameters:
- title (string, required)
- url (string, optional)
- text (string, optional)
At least one of url/text must be provided. All three together is allowed (HN supports it).

Config: add a new `cookie` key to the root manifest.json (required: false; the tool errors clearly if absent so other tools keep working without it). Description should tell the user it's the value of HN's `user` cookie.

Flow:
1. GET https://news.ycombinator.com/ with `Cookie: user=<value>`. Parse the logged-in username from the header (`<a href="user?id=USERNAME">`). If absent, return 'invalid or expired cookie' error.
2. GET /submit with the same cookie. Parse hidden form inputs `fnid` and `fnop`.
3. POST /r as form-encoded with `fnid`, `fnop`, `title`, `url`, `text` (allow_redirects=False, follow at most one redirect manually if needed). Send empty strings for omitted url/text.
4. Inspect response: if it returns the submit page again with a visible error (e.g. dupe, validation), surface that error text. Otherwise treat as success.
5. GET /submitted?id=<username>, find the most recent row whose title matches the submitted title, return its id and item URL.

Return value on success: { "id": <int>, "url": "https://news.ycombinator.com/item?id=<id>" }. On expected failures (missing cookie, invalid cookie, dupe, validation, rate-limit), exit non-zero with a clear stderr message.

Also update README.md: document the new tool, parameters, and how to obtain the `user` cookie value (browser devtools -> Application -> Cookies -> news.ycombinator.com -> `user`). Mention that the cookie is long-lived but can be invalidated by logging out.

Non-goals: editing/deleting submissions, upvoting, commenting, retry logic, username/password login.

## Acceptance Criteria

- Submitting a valid title+url returns the new item's id and URL.
- Missing cookie config produces a clear error, not a stack trace.
- Invalid/expired cookie produces a clear error.
- Dupe and other HN-side validation errors are surfaced as readable strings.
- Existing tools (get_front_page, stalk) continue to work unchanged.

