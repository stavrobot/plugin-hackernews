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

## Configuration

- `api_key` (required): OpenAI API key used by the `stalk` tool.
- `model` (optional): OpenAI model for analysis. Defaults to `gpt-5.2`.
