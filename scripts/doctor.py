#!/usr/bin/env python3
"""Check the local environment for the SEO skill."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent


def module_status(name: str) -> dict:
    spec = importlib.util.find_spec(name)
    return {"installed": spec is not None}


def command_status(cmd: str) -> dict:
    path = shutil.which(cmd)
    return {"available": bool(path), "path": path}


def run_subprocess(command: list[str], timeout: int = 20) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def https_probe() -> dict:
    req = urllib.request.Request("https://example.com", headers={"User-Agent": "CodexSEO-Doctor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ssl.create_default_context()) as resp:
            return {"ok": True, "status": getattr(resp, "status", None), "final_url": resp.geturl()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def requests_https_probe() -> dict:
    if importlib.util.find_spec("requests") is None:
        return {"ok": False, "error": "requests not installed"}

    import requests  # type: ignore

    try:
        resp = requests.get("https://example.com", timeout=15, headers={"User-Agent": "CodexSEO-Doctor/1.0"})
        return {"ok": True, "status": resp.status_code, "final_url": resp.url}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Output JSON.")
    args = parser.parse_args()

    results = {
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
        },
        "modules": {
            "requests": module_status("requests"),
            "beautifulsoup4": module_status("bs4"),
            "playwright": module_status("playwright"),
        },
        "commands": {
            "gh": command_status("gh"),
            "git": command_status("git"),
        },
        "probes": {
            "urllib_https": https_probe(),
            "requests_https": requests_https_probe(),
        },
        "playwright": {
            "chromium_install_check": run_subprocess([sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"], timeout=30)
            if importlib.util.find_spec("playwright") is not None
            else {"ok": False, "error": "playwright not installed"},
        },
        "freshness_lint_command": f'{sys.executable} "{SCRIPT_DIR / "lint_freshness.py"}" --json',
        "skill_dir": str(SKILL_DIR),
    }

    if args.json:
        print(json.dumps(results, indent=2))
        return 0

    print("SEO Skill Doctor")
    print("=" * 40)
    print(f"Python: {results['python']['version']} ({results['python']['executable']})")
    print()
    print("Modules:")
    for name, status in results["modules"].items():
        print(f"  {'OK' if status['installed'] else 'MISSING'} {name}")
    print()
    print("Commands:")
    for name, status in results["commands"].items():
        print(f"  {'OK' if status['available'] else 'MISSING'} {name}" + (f" -> {status['path']}" if status["path"] else ""))
    print()
    print("Network probes:")
    for name, status in results["probes"].items():
        if status.get("ok"):
            print(f"  OK {name}: {status.get('status')} {status.get('final_url')}")
        else:
            print(f"  FAIL {name}: {status.get('error')}")
    print()
    if results["playwright"]["chromium_install_check"].get("ok"):
        print("Playwright: OK dry-run install check passed")
    else:
        print(f"Playwright: {results['playwright']['chromium_install_check'].get('error') or results['playwright']['chromium_install_check'].get('stderr')}")
    print()
    print(f"Freshness lint: {results['freshness_lint_command']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
