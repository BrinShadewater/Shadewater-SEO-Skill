#!/usr/bin/env python3
"""Make stdout/stderr safe for the emoji and box-drawing characters these scripts print.

The problem this solves, on Windows:

Python picks the encoding for stdout from the locale when stdout is not a terminal.
On this machine that is cp1252, which cannot represent any of the ~53 non-Latin-1
characters the SEO scripts use (emoji status markers, arrows, box drawing, the
info glyph). Printing one raises UnicodeEncodeError. Two consequences, the second
much worse than the first:

1. Interactive runs crash partway through with a traceback.
2. **Redirected runs produce a zero-byte file.** `python robots_checker.py --json > out.json`
   dies on the first emoji, having written nothing, and the caller sees an empty
   file rather than an error. Silent data loss.

Importing this module reconfigures both streams to UTF-8 with `errors="replace"`,
so the characters survive where the console supports them and degrade to a
replacement character where it does not. Either way nothing raises and nothing
truncates.

Usage — one line, immediately after the stdlib imports:

    import console_safe  # noqa: F401  (side effect: UTF-8 stdout/stderr)

Idempotent and safe to import from a module that is itself imported.
"""

from __future__ import annotations

import sys


def enable(errors: str = "replace") -> None:
    """Reconfigure stdout/stderr to UTF-8. Safe to call more than once."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            # Not a TextIOWrapper (pytest capture, some embedded runtimes). Leave it
            # alone rather than replacing a stream we do not own.
            continue
        try:
            reconfigure(encoding="utf-8", errors=errors)
        except (ValueError, OSError):
            # Detached or already-closed stream. Printing is the caller's problem
            # at that point; do not make importing this module fatal.
            pass


enable()
