#!/usr/bin/env python3
"""Check that SEO skill reference files include Updated metadata and are not stale."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path


DEFAULT_ROOTS = ("resources/references", "resources/templates", "resources/skills", "resources/agents")
UPDATED_RE = re.compile(r"<!--\s*Updated:\s*(\d{4}-\d{2}-\d{2})\s*-->")


def check_file(path: Path, stale_days: int) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = UPDATED_RE.search(text)
    result = {"path": str(path), "has_updated": bool(match), "date": None, "stale": None}
    if not match:
        return result

    updated = datetime.strptime(match.group(1), "%Y-%m-%d").date()
    age = (date.today() - updated).days
    result["date"] = updated.isoformat()
    result["age_days"] = age
    result["stale"] = age > stale_days
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", action="append", help="Directory to scan. Repeatable.")
    parser.add_argument("--stale-days", type=int, default=90)
    parser.add_argument("--json", action="store_true", help="Output JSON.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    roots = [skill_dir / root for root in (args.root or DEFAULT_ROOTS)]
    files = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json"}:
                files.append(check_file(path, args.stale_days))

    missing = [item for item in files if not item["has_updated"]]
    stale = [item for item in files if item["has_updated"] and item.get("stale")]
    payload = {
        "checked_files": len(files),
        "missing_updated": missing,
        "stale_files": stale,
        "ok": not missing and not stale,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0 if payload["ok"] else 1

    print("SEO Freshness Lint")
    print("=" * 40)
    print(f"Checked: {payload['checked_files']}")
    print(f"Missing Updated tag: {len(missing)}")
    print(f"Stale files: {len(stale)}")
    if missing:
        print("\nMissing Updated tag:")
        for item in missing:
            print(f"  {item['path']}")
    if stale:
        print("\nStale files:")
        for item in stale:
            print(f"  {item['path']} ({item['age_days']} days)")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
