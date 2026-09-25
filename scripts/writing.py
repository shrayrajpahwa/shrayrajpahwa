"""Rewrite the writing section of README.md from the newsletters' RSS feeds. Stdlib only."""

from __future__ import annotations

import re
import sys
import urllib.request
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

FEEDS = {
    "x&y": "https://xandyregression.substack.com/feed",
    "shrelly": "https://shrelly.substack.com/feed",
}
LIMIT = 6
START, END = "<!-- writing:start -->", "<!-- writing:end -->"


def tag(chunk: str, name: str) -> str:
    m = re.search(rf"<{name}>(.*?)</{name}>", chunk, re.S)
    if not m:
        return ""
    raw = re.sub(r"^\s*<!\[CDATA\[(.*?)\]\]>\s*$", r"\1", m.group(1), flags=re.S)
    return unescape(raw).strip()


def items(source: str, xml: str) -> list[tuple[object, str, str, str]]:
    out = []
    for chunk in xml.split("<item>")[1:]:
        title, link, date = tag(chunk, "title"), tag(chunk, "link"), tag(chunk, "pubDate")
        if title and link and date:
            out.append((parsedate_to_datetime(date), title, link, source))
    return out


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def render(rows: list[tuple[object, str, str, str]]) -> str:
    if not rows:
        return "nothing yet."
    lines = []
    for when, title, link, source in rows[:LIMIT]:
        stamp = when.strftime("%d/%m/%Y")  # type: ignore[attr-defined]
        title = title.replace("[", "(").replace("]", ")")
        lines.append(f"- [{title}]({link}) · {source} · {stamp}")
    return "\n".join(lines)


def main() -> int:
    rows: list[tuple[object, str, str, str]] = []
    for source, url in FEEDS.items():
        try:
            rows += items(source, fetch(url))
        except OSError as e:  # one feed down should not blank the section
            print(f"skip {source}: {e}", file=sys.stderr)
    rows.sort(key=lambda r: r[0], reverse=True)  # type: ignore[arg-type,return-value]
    readme = Path("README.md")
    text = readme.read_text()
    new = re.sub(
        rf"{re.escape(START)}.*?{re.escape(END)}",
        f"{START}\n{render(rows)}\n{END}",
        text,
        flags=re.S,
    )
    if new != text:
        readme.write_text(new)
        print("README updated")
    else:
        print("no change")
    return 0


if __name__ == "__main__":
    sys.exit(main())
