#!/usr/bin/env python3
"""Fetch each lesson's wordlist from its video description.

The channel publishes the vocabulary for each lesson in the video description,
so there is no need to transcribe anything: the words, readings and glosses are
already written down. This script saves each description to ``sources/`` and
stops there — parsing happens separately, in parse_wordlists.py.

The saved files are committed. That is the point: after the first fetch the
build never touches the network, so it keeps working if a description is edited,
a video is made private, or YouTube changes its page markup. Re-run this only to
deliberately re-sync with the channel, and read the diff when you do.

    uv run python scripts/fetch_wordlists.py [--lesson N] [--force]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from lib import playlist  # noqa: E402

ROOT = Path(__file__).parent.parent

# A desktop UA: YouTube serves a stripped page to unrecognised clients, and the
# description is not in it.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# The description lives in the ytInitialPlayerResponse JSON embedded in the page.
_DESCRIPTION_RE = re.compile(r'"shortDescription":"(.*?)","isCrawlable"', re.S)
_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)


def fetch_page(video_id: str, *, timeout: int = 30) -> str:
    request = urllib.request.Request(
        f"https://www.youtube.com/watch?v={video_id}",
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_description(page: str, video_id: str) -> str:
    match = _DESCRIPTION_RE.search(page)
    if not match:
        raise ValueError(
            f"no description found for {video_id}. YouTube may have changed its "
            f"page structure, or served a consent/bot wall."
        )
    # The captured group is a JSON string body, so let json decode the escapes
    # (\n, 【, ...) rather than hand-rolling it.
    return json.loads(f'"{match.group(1)}"')


def extract_title(page: str) -> str:
    match = _TITLE_RE.search(page)
    return match.group(1).replace(" - YouTube", "").strip() if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lesson", type=int, help="fetch one lesson only")
    parser.add_argument("--force", action="store_true", help="refetch lessons already saved")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    args = parser.parse_args()

    lessons = playlist.LESSONS
    if args.lesson:
        lessons = [entry for entry in lessons if entry[0] == args.lesson]
        if not lessons:
            parser.error(f"no lesson {args.lesson}; playlist has 1-{len(playlist.LESSONS)}")

    failures = 0
    for number, video_id, _theme in lessons:
        destination = ROOT / playlist.source_path(number)
        if destination.exists() and not args.force:
            print(f"lesson {number:02d}  already saved ({destination.name})")
            continue
        try:
            page = fetch_page(video_id)
            description = extract_description(page, video_id)
        except (urllib.error.URLError, ValueError, TimeoutError) as error:
            print(f"lesson {number:02d}  FAILED: {error}", file=sys.stderr)
            failures += 1
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(description, encoding="utf-8")
        print(f"lesson {number:02d}  {len(description):5d} chars  {extract_title(page)[:60]}")
        time.sleep(args.delay)

    if failures:
        print(f"\n{failures} lesson(s) failed", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
