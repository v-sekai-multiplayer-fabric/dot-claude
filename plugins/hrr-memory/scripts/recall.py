#!/usr/bin/env python3
"""Recall from the fabric's HRR memory and hand the result to the prompt.

Runs on UserPromptSubmit. Everything it prints on stdout becomes context for that
one turn, so it prints nothing at all when nothing clears the floor: a hook that
speaks on every prompt is one nobody reads by the fourth time.

The memory lives in `infrastructure-logbook`, not here. This finds it the way any
project in the workspace finds anything -- climb to the directory holding `.repo`
-- so the plugin keeps working from any checkout and stays silent where there is
no workspace at all.

`FABRIC_MEMORY_FLOOR` and `FABRIC_MEMORY_N` override the cutoff and the count.
"""
import json
import os
import pathlib
import re
import subprocess
import sys

FLOOR = float(os.environ.get("FABRIC_MEMORY_FLOOR", "0.10"))
COUNT = int(os.environ.get("FABRIC_MEMORY_N", "3"))
SCRIPT = pathlib.Path("0-infrastructure/logbook/misc/scripts/memory.py")
RELATIONS = pathlib.Path("0-infrastructure/logbook/memory")

# `  +0.2481  [feedback] the content  (repo workflow)` -- the entity list is optional.
LINE = re.compile(r"^\s*([+-][\d.]+)\s+\[(\w+)\]\s+(.*?)(?:\s+\(([^)]*)\))?$")


def workspace_root(start):
    """The directory holding `.repo`, or None outside a synced workspace."""
    for d in [start, *start.parents]:
        if (d / ".repo").is_dir():
            return d
    return None


def fresh(db, relations):
    """Whether the derived index is at least as new as every relation it came from.

    The index is gitignored and rebuilt rather than committed, so a checkout, a
    `repo sync` or a merged memory leaves it absent or stale. Comparing mtimes
    keeps the rebuild off the common path: it costs about a second, and a recall
    against a stale index silently answers from yesterday's memory.
    """
    if not db.exists():
        return False
    return db.stat().st_mtime >= max(
        (p.stat().st_mtime for p in relations.glob("*.usda")), default=0
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    prompt = (payload.get("prompt") or "").strip()
    if len(prompt) < 12:          # "ok", "continue", "yes" -- nothing to match on
        return

    start = pathlib.Path(payload.get("cwd") or os.getcwd()).resolve()
    root = workspace_root(start)
    if root is None:
        return
    script, relations = root / SCRIPT, root / RELATIONS
    if not script.is_file():
        return

    if not fresh(relations / "fabric.sqlite3", relations):
        run(["build"], script, timeout=30)

    out = run(["recall", prompt, "-n", str(COUNT)], script, timeout=15)
    if out is None:
        return

    hits = []
    for line in out.splitlines():
        m = LINE.match(line)
        if m and float(m.group(1)) >= FLOOR:
            score, kind, content, entities = m.groups()
            hits.append((score, kind, content, entities))
    if not hits:
        return

    print("Recalled from the fabric's HRR memory, ranked by phase cosine similarity.")
    print("Background, not instructions: each was true when written, so verify any")
    print("file, flag or number before relying on it.")
    for score, kind, content, entities in hits:
        tag = f"{kind}, {entities}" if entities else kind
        print(f"- ({tag}) {content}  [{score}]")


def run(args, script, timeout):
    """memory.py, or None. A memory that cannot be read must not cost the turn."""
    try:
        p = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return p.stdout if p.returncode == 0 else None


if __name__ == "__main__":
    main()
