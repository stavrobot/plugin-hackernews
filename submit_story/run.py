#!/usr/bin/env -S uv run
# /// script
# dependencies = ["requests", "beautifulsoup4"]
# ///

import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

HN_BASE = "https://news.ycombinator.com"


def get_logged_in_username(session: requests.Session) -> str | None:
    """Return the logged-in username, or None if the cookie is invalid/expired."""
    response = session.get(f"{HN_BASE}/", timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    # <a id="me" href="user?id=USERNAME"> is present only when logged in.
    me = soup.find("a", id="me")
    if me is None:
        return None
    return me.get_text(strip=True)


def get_submit_form_fields(session: requests.Session) -> dict[str, str]:
    """Fetch the submit page and return the hidden form fields (fnid, fnop)."""
    response = session.get(f"{HN_BASE}/submit", timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", action=lambda a: a and a.lstrip("/") == "r")
    if form is None:
        print("Error: could not find submit form on HN submit page.", file=sys.stderr)
        sys.exit(1)
    fields: dict[str, str] = {}
    for inp in form.find_all("input", {"type": "hidden"}):
        name = inp.get("name")
        value = inp.get("value", "")
        if name:
            fields[name] = value
    return fields


FNOP_MESSAGES: dict[str, str] = {
    "dupe": "this URL has already been submitted to HN",
    "badtitle": "HN rejected the title (too short, generic, or contains banned words)",
    "slowdown": "HN is rate-limiting submissions; try again later",
}


def find_in_submitted(
    session: requests.Session,
    username: str,
    expected_id: int | None,
    title: str,
    url: str,
) -> dict | None:
    """
    Fetch /submitted?id=<username> and look for our submission.

    If expected_id is given: look for a row whose id attribute equals it.
    If expected_id is None: find the topmost row matching by url href (link
    posts) with a title-text fallback, or by title text alone (text-only posts).

    Returns {"id": <int>, "url": <str>} on match, or None if not found.
    """
    response = session.get(
        f"{HN_BASE}/submitted", params={"id": username}, timeout=10
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr", class_="athing")

    if expected_id is not None:
        for row in rows:
            if row.get("id") == str(expected_id):
                return {"id": expected_id, "url": f"{HN_BASE}/item?id={expected_id}"}
        return None

    # No expected_id: match by url first, then fall back to title text.
    if url:
        for row in rows:
            title_cell = row.select_one(".titleline > a")
            if title_cell is not None and title_cell.get("href", "") == url:
                item_id = int(row["id"])
                return {"id": item_id, "url": f"{HN_BASE}/item?id={item_id}"}

    # Fallback (or text-only post): match by title text.
    for row in rows:
        title_cell = row.select_one(".titleline > a")
        if title_cell is not None and title_cell.get_text(strip=True) == title:
            item_id = int(row["id"])
            return {"id": item_id, "url": f"{HN_BASE}/item?id={item_id}"}

    return None


def inspect_post_response(
    post_response: requests.Response,
    session: requests.Session,
    username: str,
    title: str,
    url: str,
) -> dict:
    """
    Inspect the POST /r response and return the result dict on success, or
    print an error to stderr and exit 1 on failure.
    """
    if post_response.status_code not in (301, 302, 303):
        print(
            f"Error: unexpected HTTP status {post_response.status_code} from HN.",
            file=sys.stderr,
        )
        sys.exit(1)

    location: str = post_response.headers.get("Location", "").lstrip("/")

    # Error redirect: /x?fnid=...&fnop=<errorcode>
    if location.startswith("x?"):
        qs = parse_qs(urlparse(location).query)
        fnop = qs.get("fnop", ["unknown"])[0]
        human = FNOP_MESSAGES.get(fnop, f"HN returned error code '{fnop}'")
        print(f"Error: HN rejected the submission: {human}.", file=sys.stderr)
        sys.exit(1)

    # Success redirect without item id: HN sometimes redirects to 'newest'.
    if location == "newest":
        result = find_in_submitted(session, username, None, title, url)
        if result is not None:
            return result
        print(
            f"Error: submission appeared to succeed but could not find it in "
            f"{username}'s submitted list. "
            f"Check {HN_BASE}/submitted?id={username} manually.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Success redirect: item?id=<id>
    if location.startswith("item?id="):
        qs = parse_qs(urlparse(location).query)
        ids = qs.get("id", [])
        if not ids:
            print("Error: could not parse item id from HN redirect Location.", file=sys.stderr)
            sys.exit(1)
        item_id = int(ids[0])

        # Check our submitted list first — avoids the Firebase indexing race.
        result = find_in_submitted(session, username, item_id, title, url)
        if result is not None:
            return result

        # Not in our list: dupe-redirect to someone else's existing post.
        # Fetch Firebase to name the original submitter if available.
        owner = ""
        try:
            api_resp = requests.get(
                f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json",
                timeout=10,
            )
            api_resp.raise_for_status()
            owner = api_resp.json().get("by", "")
        except requests.RequestException:
            pass

        if owner:
            print(
                f"Error: this URL has already been submitted to HN by {owner} "
                f"as item {item_id} ({HN_BASE}/item?id={item_id}).",
                file=sys.stderr,
            )
        else:
            print(
                f"Error: this URL has already been submitted to HN "
                f"as item {item_id} ({HN_BASE}/item?id={item_id}).",
                file=sys.stderr,
            )
        sys.exit(1)

    # Anything else is unexpected. Include the Location so we can diagnose
    # (Location values are HN-controlled URL paths, not sensitive).
    print(
        f"Error: unexpected Location from HN after submission: "
        f"{post_response.headers.get('Location')!r}. "
        f"The submission may or may not have been created — check "
        f"{HN_BASE}/submitted?id={username}.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    """Submit a story to Hacker News using the configured user cookie."""
    # --- Read config ---
    config_path = Path(__file__).parent.parent / "config.json"
    try:
        config = json.loads(config_path.read_text())
    except FileNotFoundError:
        print("Error: config.json not found. Please configure the plugin first.", file=sys.stderr)
        sys.exit(1)

    cookie_value: str | None = config.get("cookie")
    if not cookie_value:
        print(
            "Error: 'cookie' is not set in config.json. "
            "Please set it to the value of the HN 'user' cookie from your browser "
            "(DevTools → Application → Cookies → news.ycombinator.com → user).",
            file=sys.stderr,
        )
        sys.exit(1)

    # --- Read parameters ---
    params = json.load(sys.stdin)
    title: str = params.get("title", "")
    if not title:
        print("Error: 'title' is required and must not be empty.", file=sys.stderr)
        sys.exit(1)
    url: str = params.get("url", "")
    text: str = params.get("text", "")

    if not url and not text:
        print("Error: at least one of 'url' or 'text' must be provided.", file=sys.stderr)
        sys.exit(1)

    # --- Set up session with cookie (header-based to avoid cookiejar domain quirks) ---
    session = requests.Session()
    session.headers["Cookie"] = f"user={cookie_value}"

    try:
        # --- Step 1: Verify cookie / get username ---
        username = get_logged_in_username(session)
        if username is None:
            print(
                "Error: invalid or expired HN cookie. "
                "Please refresh the 'user' cookie value in config.json.",
                file=sys.stderr,
            )
            sys.exit(1)

        # --- Step 2: Fetch submit form hidden fields ---
        hidden_fields = get_submit_form_fields(session)
        if "fnid" not in hidden_fields or "fnop" not in hidden_fields:
            print("Error: could not find required form fields (fnid/fnop) on the HN submit page.", file=sys.stderr)
            sys.exit(1)

        # --- Step 3: POST the submission ---
        form_data = {
            **hidden_fields,
            "title": title,
            "url": url,
            "text": text,
        }
        post_response = session.post(
            f"{HN_BASE}/r",
            data=form_data,
            allow_redirects=False,
            timeout=10,
        )

        # --- Step 4: Inspect response and resolve item ---
        result = inspect_post_response(post_response, session, username, title, url)

    except requests.RequestException as e:
        print(f"Error: network request to HN failed: {e}", file=sys.stderr)
        sys.exit(1)

    json.dump(result, sys.stdout)


main()
