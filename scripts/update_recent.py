#!/usr/bin/env python3
"""
Fetches the N most recently pushed-to repos for a GitHub user and
rewrites the markdown table between RECENT_ACTIVITY markers in README.md.
"""
import os
import re
import sys
import urllib.request
import json
from datetime import datetime, timezone

USERNAME = "Michael-Mokua"
README_PATH = "README.md"
N_REPOS = 4
TOKEN = os.environ.get("GITHUB_TOKEN", "")

START_MARKER = "<!-- RECENT_ACTIVITY:START -->"
END_MARKER = "<!-- RECENT_ACTIVITY:END -->"


def fetch_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos?sort=pushed&direction=desc&per_page=100"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-readme-bot",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    # exclude the profile repo itself and forks
    data = [r for r in data if not r.get("fork") and r["name"].lower() != USERNAME.lower()]
    return data[:N_REPOS]


def relative_time(iso_ts):
    pushed = datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - pushed
    secs = delta.total_seconds()
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


def build_table(repos):
    lines = ["| Repo | Last Push |", "|---|---|"]
    for r in repos:
        name = r["name"]
        url = r["html_url"]
        when = relative_time(r["pushed_at"])
        lines.append(f"| [{name}]({url}) | {when} |")
    return "\n".join(lines)


def update_readme(table_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = re.compile(
        re.escape(START_MARKER) + r".*?" + re.escape(END_MARKER),
        re.DOTALL,
    )
    replacement = f"{START_MARKER}\n{table_md}\n{END_MARKER}"

    if not pattern.search(content):
        print("Markers not found in README.md — aborting without changes.", file=sys.stderr)
        sys.exit(1)

    new_content = pattern.sub(replacement, content)

    if new_content == content:
        print("No change in recent activity — skipping write.")
        return False

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    return True


def main():
    repos = fetch_repos()
    if not repos:
        print("No repos returned — aborting without changes.", file=sys.stderr)
        sys.exit(1)
    table_md = build_table(repos)
    changed = update_readme(table_md)
    print("README updated." if changed else "README unchanged.")


if __name__ == "__main__":
    main()
