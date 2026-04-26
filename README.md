# Hackernews plugin

Fetch stories and data from Hacker News using the official API.

This plugin also includes a user-analysis tool powered by OpenAI.

## Installation

Ask Stavrobot to install https://github.com/stavrobot/plugin-hackernews.git.

## Tools

### `get_front_page`

Fetch the top stories from the Hacker News front page. Returns title, URL, author, score, comment count, and timestamp for each story.

**Parameters:**

- `limit` (integer, optional): Number of stories to fetch (1–500). Defaults to 30.

### `stalk`

Analyze a Hacker News user's comment history with OpenAI to answer a question about them.

**Parameters:**

- `username` (string, required): The Hacker News username to analyze.
- `question` (string, required): The question to answer about the user.

### `submit_story`

Submit a story (link post or text post) to Hacker News on behalf of the configured user.
Requires the `cookie` config value to be set (see Configuration below).

**Parameters:**

- `title` (string, required): The title of the story.
- `url` (string, optional): The URL to submit. At least one of `url` or `text` must be provided.
- `text` (string, optional): Body text for a text post. Can be combined with a URL.

**Returns:** `{ "id": <item id>, "url": "https://news.ycombinator.com/item?id=<id>" }`

## Configuration

- `api_key` (required): OpenAI API key used by the `stalk` tool.
- `model` (optional): OpenAI model for analysis. Defaults to `gpt-5.2`.
- `cookie` (optional): Value of the HN `user` cookie. Required only for `submit_story`.

### Obtaining the HN `user` cookie

1. Log in to [news.ycombinator.com](https://news.ycombinator.com) in your browser.
2. Open DevTools (F12) → **Application** tab → **Cookies** → `https://news.ycombinator.com`.
3. Find the cookie named `user` and copy its **Value** (a long alphanumeric string).
4. Set that value as `cookie` in the plugin configuration.

The `user` cookie is long-lived but will be invalidated if you log out of HN.
If `submit_story` reports an invalid or expired cookie, repeat the steps above to get a fresh value.
