#!/usr/bin/env -S uv run
# /// script
# dependencies = ["requests"]
# ///

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests

BASE_URL = "https://hacker-news.firebaseio.com/v0"


def fetch_item(item_id: int) -> dict | None:
    """Fetch a single item from the HN API."""
    response = requests.get(f"{BASE_URL}/item/{item_id}.json", timeout=10)
    response.raise_for_status()
    return response.json()


def format_story(item: dict) -> dict:
    """Format a story item into a clean response object."""
    timestamp = item.get("time", 0)
    created_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "url": item.get("url"),
        "text": item.get("text"),
        "author": item.get("by"),
        "score": item.get("score", 0),
        "comment_count": item.get("descendants", 0),
        "created_at": created_at,
        "type": item.get("type"),
    }


def main() -> None:
    """Fetch the top stories from the HN front page."""
    params = json.load(sys.stdin)
    limit = params.get("limit", 30)
    limit = max(1, min(500, limit))

    # Fetch the list of top story IDs.
    response = requests.get(f"{BASE_URL}/topstories.json", timeout=10)
    response.raise_for_status()
    story_ids = response.json()[:limit]

    # Fetch each story in parallel.
    stories = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        future_to_id = {executor.submit(fetch_item, sid): sid for sid in story_ids}
        results = {}
        for future in as_completed(future_to_id):
            story_id = future_to_id[future]
            item = future.result()
            if item:
                results[story_id] = item

    # Preserve the original ranking order.
    for story_id in story_ids:
        if story_id in results:
            stories.append(format_story(results[story_id]))

    json.dump({"stories": stories, "count": len(stories)}, sys.stdout)


main()
