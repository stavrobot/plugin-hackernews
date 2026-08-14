---
id: ph-omdqm
status: closed
deps: []
links: []
created: 2026-08-14T19:30:37Z
type: task
priority: 2
assignee: Stavros Korokithakis
---
# stalk: parameterize max_comments, bound item scan, raise concurrency

Objective: make the comment-history scrape in stalk/run.py bounded and caller-controllable.

Scope: stalk/run.py, stalk/manifest.json, README.md (stalk section only).

Changes:
- New optional tool parameter max_comments (integer), default 600, clamped to 1-2000. Add it to KNOWN_PARAMS so the existing strict unknown-parameter rejection still works.
- Replace the MAX_COMMENTS constant with the parameter value threaded into fetch_comments.
- Add a hardcoded item scan ceiling of max_comments * 5. Stop fetching when either the comment target is reached OR that many submitted IDs have been examined, whichever comes first.
- MAX_WORKERS 5 -> 10. Stays a hardcoded constant: not a tool parameter, not a config value.
- Truncate the collected comments so max_comments is exact. Today the loop breaks only after a full batch, so it overshoots.
- Output gains comments_analyzed: {"analysis": ..., "comments_analyzed": N}.
- Per-item fetch failures must be skipped, not fatal. A single transient error currently propagates out of future.result() and kills the whole run, which matters now that request volume is up to ~3000. The initial user lookup stays fatal.
- If zero comments are found, error out with a clear message instead of sending an empty prompt to OpenAI.

Non-goals:
- No comment tree / ancestor / thread-depth traversal. The submitted list is flat and stays that way.
- Do not expose concurrency as a parameter or config value.
- No global wall-clock deadline. The item ceiling is the bound.
- No caching, retries, or rate-limit backoff.
- Do not touch get_front_page or submit_story.

Constraints:
- Keep the existing per-request timeout=10.
- No new dependencies.
- A default call must behave as it does today apart from speed and the new output field.

ready for implementation

## Design

The scan ceiling is a multiple of max_comments rather than a fixed number so the bound scales with what the caller asked for. Rationale for bounding at all: the loop otherwise walks the user's entire submitted list, which for a link-heavy user with tens of thousands of submissions means tens of thousands of HTTP requests. 5x means a user whose submissions are under ~20 percent comments gets cut off early, which is generous for typical HN users.

max_comments is preferred over a max_items parameter because the cost that actually bites is the LLM prompt size, and because max_items can silently yield very few comments for a story-heavy user. comments_analyzed in the output exists so a shortfall caused by the ceiling is visible to the caller instead of silent.

Note that MAX_WORKERS currently doubles as the batch stride in fetch_comments. Keeping that coupling is fine; it is why the overshoot fix (explicit truncation) is needed.

