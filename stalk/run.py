#!/usr/bin/env -S uv run
# /// script
# dependencies = ["requests", "openai"]
# ///

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from openai import OpenAI

BASE_URL = "https://hacker-news.firebaseio.com/v0"
MAX_COMMENTS = 600
MAX_WORKERS = 5

KNOWN_PARAMS = {"username", "question"}


def fetch_item(item_id: int) -> dict | None:
    response = requests.get(f"{BASE_URL}/item/{item_id}.json", timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_comments(submitted: list[int]) -> list[str]:
    # Submit IDs in batches so we stop making HTTP requests once we have enough
    # comments. Submitting all IDs upfront would trigger one request per
    # submission even for users with thousands of submissions.
    comments: list[str] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for batch_start in range(0, len(submitted), MAX_WORKERS):
            batch = submitted[batch_start : batch_start + MAX_WORKERS]
            futures = [executor.submit(fetch_item, item_id) for item_id in batch]
            for future in as_completed(futures):
                item = future.result()
                if item and item.get("type") == "comment" and item.get("text"):
                    comments.append(item["text"])
            if len(comments) >= MAX_COMMENTS:
                break
    return comments


def analyze_comments(username: str, comments: list[str], question: str, api_key: str, model: str) -> str:
    client = OpenAI(api_key=api_key)

    comments_joined = "\n\n".join(comments)
    prompt = (
        f"Below is the comment history of Hacker News user '{username}'. "
        "Please answer the following question based on information you can derive from the comments. "
        "Provide reasoning for your conclusion. If there's not enough information, say so.\n\n"
        f"Question: {question}\n\n"
        f"Comments:\n{comments_joined}"
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an analyst skilled at deducing information about people from their online comments and context clues.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    content = response.choices[0].message.content
    assert content is not None
    return content


def main() -> None:
    params = json.load(sys.stdin)

    unknown = set(params) - KNOWN_PARAMS
    if unknown:
        raise ValueError(f"Unknown parameters: {unknown}")

    username: str = params["username"]
    question: str = params["question"]

    config_path = Path(__file__).parent.parent / "config.json"
    config = json.loads(config_path.read_text())
    api_key: str = config["api_key"]
    model: str = config.get("model", "gpt-5.2")

    response = requests.get(f"{BASE_URL}/user/{username}.json", timeout=10)
    response.raise_for_status()
    user_data = response.json()

    submitted: list[int] = user_data.get("submitted", [])

    comments = fetch_comments(submitted)

    analysis = analyze_comments(username, comments, question, api_key, model)

    json.dump({"analysis": analysis}, sys.stdout)


main()
