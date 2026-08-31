#!/usr/bin/env python3
"""
Pulls live data from the GitHub API and rewrites three dynamic regions
of README.md between marker comments:

  1. RECENT_ACTIVITY  - table of the N most recently pushed repos
  2. TYPING_SVG        - the animated typing banner (repo count baked into its URL)
  3. WHOAMI            - the whoami/status code block (repo count + currently-shipping repo)

Everything outside these marker blocks (pinned project write-ups, stats
widgets, etc.) is left untouched — those stay hand-curated on purpose.
"""
import os
import re
import sys
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

USERNAME = "Michael-Mokua"
README_PATH = "README.md"
N_REPOS = 4
TOKEN = os.environ.get("GITHUB_TOKEN", "")

RECENT_START, RECENT_END = "<!-- RECENT_ACTIVITY:START -->", "<!-- RECENT_ACTIVITY:END -->"
TYPING_START, TYPING_END = "<!-- TYPING_SVG:START -->", "<!-- TYPING_SVG:END -->"
WHOAMI_START, WHOAMI_END = "<!-- WHOAMI:START -->", "<!-- WHOAMI:END -->"


def api_get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-readme-bot",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def fetch_user():
    return api_get(f"https://api.github.com/users/{USERNAME}")


def fetch_repos():
    data = api_get(
        f"https://api.github.com/users/{USERNAME}/repos"
        "?sort=pushed&direction=desc&per_page=100"
    )
    return [r for r in data if not r.get("fork") and r["name"].lower() != USERNAME.lower()]


def relative_time(iso_ts):
    pushed = datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    secs = (datetime.now(timezone.utc) - pushed).total_seconds()
    if secs < 90:
        return "just now"
    mins = secs / 60
    if mins < 60:
        return f"{int(mins)} min ago"
    hours = mins / 60
    if hours < 24:
        return f"{int(hours)} hour{'s' if int(hours) != 1 else ''} ago"
    days = hours / 24
    if days < 2:
        return "yesterday"
    if days < 30:
        return f"{int(days)} days ago"
    months = days / 30
    if months < 12:
        return f"{int(months)} month{'s' if int(months) != 1 else ''} ago"
    years = days / 365
    return f"{int(years)} year{'s' if int(years) != 1 else ''} ago"


def build_recent_table(repos):
    lines = ["| Repo | Last Push |", "|---|---|"]
    for r in repos[:N_REPOS]:
        lines.append(f"| [{r['name']}]({r['html_url']}) | {relative_time(r['pushed_at'])} |")
    return "\n".join(lines)


def build_typing_svg(repo_count):
    typing_lines = [
        "Founder @ MIKESTH3TIC.DEV",
        "AI Software Studio \u2014 Africa-First",
        f"{repo_count} repos | Marketplaces \u00b7 ML \u00b7 Mobile \u00b7 Agentic AI",
    ]
    encoded = ";".join(urllib.parse.quote_plus(l) for l in typing_lines)
    params = {
        "font": "Courier New",
        "weight": "700",
        "size": "26",
        "duration": "2200",
        "pause": "800",
        "color": "FF00E5",
        "background": "05010A00",
        "center": "true",
        "vCenter": "true",
        "multiline": "true",
        "repeat": "true",
        "width": "900",
        "height": "150",
    }
    query = "&".join(f"{k}={urllib.parse.quote_plus(v)}" for k, v in params.items())
    url = f"https://readme-typing-svg.demolab.com/?{query}&lines={encoded}"
    return f'<img src="{url}" alt="Typing SVG" />'


def build_whoami(repo_count, top_repo_name):
    return f"""```bash
$ whoami
> Michael Ogutu Mokua — founder, MIKESTH3TIC.DEV
> AI software studio · Nairobi, Kenya 🇰🇪 · Africa-first

$ status
> final-year BSc IT @ Kabarak University (Dec 2026)
> {repo_count} repos: marketplaces · ML pipelines · agentic AI · Android · fintech
> currently shipping: {top_repo_name}

$ origin
> raised on a farm off Old Kangundo Road, Joska
> built to last, not to impress
```"""


def replace_block(content, start_marker, end_marker, new_body):
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if not pattern.search(content):
        print(f"Markers {start_marker} / {end_marker} not found — skipping that block.", file=sys.stderr)
        return content, False
    replacement = f"{start_marker}\n{new_body}\n{end_marker}"
    new_content = pattern.sub(replacement, content)
    return new_content, new_content != content


def main():
    user = fetch_user()
    repos = fetch_repos()
    if not repos:
        print("No repos returned — aborting without changes.", file=sys.stderr)
        sys.exit(1)

    repo_count = user.get("public_repos", len(repos))
    top_repo_name = repos[0]["name"]

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    any_changed = False

    content, changed = replace_block(content, RECENT_START, RECENT_END, build_recent_table(repos))
    any_changed = any_changed or changed

    content, changed = replace_block(content, TYPING_START, TYPING_END, build_typing_svg(repo_count))
    any_changed = any_changed or changed

    content, changed = replace_block(content, WHOAMI_START, WHOAMI_END, build_whoami(repo_count, top_repo_name))
    any_changed = any_changed or changed

    if not any_changed:
        print("No changes — skipping write.")
        return

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("README updated.")


if __name__ == "__main__":
    main()
