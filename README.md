# Hackernews plugin

Fetch stories and data from Hacker News using the official API.

## Installation

Ask Stavrobot to install https://github.com/stavrobot/plugin-hackernews.git.

## Tools

### `get_front_page`

Fetch the top stories from the Hacker News front page. Returns title, URL, author, score, comment count, and timestamp for each story.

**Parameters:**

- `limit` (integer, optional): Number of stories to fetch (1–500). Defaults to 30.
