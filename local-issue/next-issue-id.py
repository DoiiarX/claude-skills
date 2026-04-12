#!/usr/bin/env python3
"""
next-issue-id - Reserve the next available local issue ID

Designed for agent-friendly, non-interactive operation.
"""

import sys
import re
import argparse
from pathlib import Path
from datetime import datetime


PLACEHOLDER_TEMPLATE = """# [Placeholder] Issue #{issue_id}

**Issue ID**: #{issue_id}
**Status**: Placeholder
**Created**: {date}

---

## Note

This is a placeholder file created by next-issue-id.py to reserve issue ID #{issue_id}.

**Action required**: Rename this file to the actual issue filename format:
`{issue_id}-{{type}}-{{description}}.md`

Where:
- {{type}} = bug | feature | refactor
- {{description}} = short-description-with-hyphens

Example: `{issue_id}-bug-websocket-timeout.md`
"""


def next_issue_id(issues_dir: Path) -> str:
    """Find the next available issue ID by scanning open and closed directories."""
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


def create_placeholder(issues_dir: Path, issue_id: str, dry_run: bool = False) -> Path:
    """Create a placeholder file to reserve the issue ID."""
    open_dir = issues_dir / "open"
    placeholder_path = open_dir / f"{issue_id}-placeholder.md"

    # Check if placeholder already exists (race condition check)
    if placeholder_path.exists():
        print(f"Error: Placeholder already exists: {placeholder_path}", file=sys.stderr)
        print(f"Hint: Another process may have reserved this ID. Run again to get the next available ID.", file=sys.stderr)
        sys.exit(1)

    if dry_run:
        return placeholder_path

    # Create directory if needed
    open_dir.mkdir(parents=True, exist_ok=True)

    # Create placeholder file
    content = PLACEHOLDER_TEMPLATE.format(
        issue_id=issue_id,
        date=datetime.now().strftime("%Y-%m-%d")
    )
    placeholder_path.write_text(content, encoding="utf-8")

    return placeholder_path


def main():
    parser = argparse.ArgumentParser(
        description="Reserve the next available local issue ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Reserve next ID and create placeholder (default)
  %(prog)s

  # Reserve ID in a specific project
  %(prog)s /path/to/project/.issues

  # Query next ID without creating placeholder
  %(prog)s --query-only

  # Preview what would be created
  %(prog)s --dry-run

  # Quiet mode (only output ID, no extra info)
  %(prog)s --quiet

  # Use in a pipeline
  ISSUE_ID=$(%(prog)s --quiet)
  mv .issues/open/$ISSUE_ID-placeholder.md .issues/open/$ISSUE_ID-bug-fix.md

Output format (default):
  {issue_id}
  placeholder_path={path}

Output format (--quiet):
  {issue_id}

Exit codes:
  0 = Success
  1 = Error (directory not found, placeholder exists, etc.)
        """
    )

    parser.add_argument(
        "issues_dir",
        nargs="?",
        default=".issues",
        help="Path to .issues directory (default: .issues)"
    )

    parser.add_argument(
        "--query-only",
        action="store_true",
        help="Only query the next ID without creating placeholder"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without actually creating it"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output the issue ID (machine-readable mode)"
    )

    args = parser.parse_args()

    issues_dir = Path(args.issues_dir)

    # Validate issues directory
    if not issues_dir.exists():
        print(f"Error: Directory not found: {issues_dir}", file=sys.stderr)
        print(f"Hint: Create the directory first with: mkdir -p {issues_dir}/{{open,closed}}", file=sys.stderr)
        sys.exit(1)

    # Get next issue ID
    issue_id = next_issue_id(issues_dir)

    # Query-only mode: just print the ID
    if args.query_only:
        print(issue_id)
        return

    # Create placeholder (or dry-run)
    placeholder_path = create_placeholder(issues_dir, issue_id, dry_run=args.dry_run)

    # Output
    if args.quiet:
        # Machine-readable: just the ID
        print(issue_id)
    else:
        # Human/agent-readable: ID + path
        print(issue_id)
        if args.dry_run:
            print(f"placeholder_path={placeholder_path} (dry-run, not created)")
        else:
            print(f"placeholder_path={placeholder_path}")

        if not args.quiet and not args.dry_run:
            # Additional hint for interactive use
            print(f"# Next: Rename to {issue_id}-{{type}}-{{description}}.md", file=sys.stderr)


if __name__ == "__main__":
    main()
