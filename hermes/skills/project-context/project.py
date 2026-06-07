#!/usr/bin/env python3
"""Project context manager — get/set/list the active project."""

import sys
from pathlib import Path

STATE_FILE = Path("/data/.hermes/current_project.txt")
DEFAULT_PROJECT = "hermes"
KNOWN_PROJECTS = ["finance", "wishlist", "hermes"]


def cmd_get() -> None:
    if STATE_FILE.exists():
        print(STATE_FILE.read_text().strip())
    else:
        print(DEFAULT_PROJECT)


def cmd_set(name: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(name.strip())
    print("ok")


def cmd_list() -> None:
    current = STATE_FILE.read_text().strip() if STATE_FILE.exists() else DEFAULT_PROJECT
    for p in KNOWN_PROJECTS:
        marker = "* " if p == current else "  "
        print(f"{marker}{p}")


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] == "get":
        cmd_get()
    elif args[0] == "set" and len(args) == 2:
        cmd_set(args[1])
    elif args[0] == "list":
        cmd_list()
    else:
        print("usage: project.py get|set <name>|list", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
