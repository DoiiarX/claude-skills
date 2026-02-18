#!/usr/bin/env python3
"""
Print the next available local issue ID (zero-padded to 3 digits).

Usage:
    python3 next-issue-id.py [issues-dir]

    issues-dir: path to the .issues directory (default: .issues)

Examples:
    python3 next-issue-id.py
    python3 ~/.claude/skills/local-issue/next-issue-id.py
    python3 ~/.claude/skills/local-issue/next-issue-id.py /path/to/project/.issues
"""

import sys
import re
from pathlib import Path


def next_issue_id(issues_dir: Path = Path(".issues")) -> str:
    max_id = 0
    for subdir in ("open", "closed"):
        d = issues_dir / subdir
        if not d.is_dir():
            continue
        for f in d.iterdir():
            m = re.match(r"^(\d+)", f.name)
            if m:
                max_id = max(max_id, int(m.group(1)))
    return f"{max_id + 1:03d}"


if __name__ == "__main__":
    issues_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".issues")
    if not issues_dir.exists():
        print(f"error: directory not found: {issues_dir}", file=sys.stderr)
        sys.exit(1)
    print(next_issue_id(issues_dir))
