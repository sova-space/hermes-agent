#!/usr/bin/env python3
"""Obsidian vault CLI — git-backed note store for the Hermes agent."""

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path

VAULT_REPO = "https://github.com/sova-claw/hermes-vault.git"
VAULT_DIR = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "vault"
PULL_CACHE_SECONDS = 300


def get_token() -> str:
    token = os.environ.get("HERMES_VAULT_GIT_TOKEN", "")
    if not token:
        print("ERROR: HERMES_VAULT_GIT_TOKEN is not set", file=sys.stderr)
        sys.exit(1)
    return token


def get_allow_dirs() -> list[str]:
    raw = os.environ.get("HERMES_VAULT_ALLOW_DIRS", "agent-inbox,daily")
    return [d.strip() for d in raw.split(",") if d.strip()]


def check_write_allowed(path: str) -> None:
    parts = Path(path).parts
    if not parts:
        print(f"ERROR: invalid path: {path}", file=sys.stderr)
        sys.exit(1)
    top_dir = parts[0]
    allow_dirs = get_allow_dirs()
    if top_dir not in allow_dirs:
        print(
            f"ERROR: writes to '{top_dir}/' are not allowed. "
            f"Allowed dirs: {', '.join(allow_dirs)}",
            file=sys.stderr,
        )
        sys.exit(1)


def git_run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(VAULT_DIR), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def ensure_vault() -> None:
    token = get_token()
    if not VAULT_DIR.exists():
        VAULT_DIR.parent.mkdir(parents=True, exist_ok=True)
        auth_url = VAULT_REPO.replace("https://", f"https://{token}@")
        result = subprocess.run(["git", "clone", auth_url, str(VAULT_DIR)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"ERROR: clone failed: {result.stderr.strip()}", file=sys.stderr)
            sys.exit(1)
        (VAULT_DIR / ".last-pull").write_text(str(time.time()))
        return

    pull_cache = VAULT_DIR / ".last-pull"
    last = float(pull_cache.read_text()) if pull_cache.exists() else 0.0
    if time.time() - last < PULL_CACHE_SECONDS:
        return

    auth_url = VAULT_REPO.replace("https://", f"https://{token}@")
    subprocess.run(["git", "-C", str(VAULT_DIR), "remote", "set-url", "origin", auth_url], capture_output=True)
    result = git_run("pull", "--ff-only", check=False)
    if result.returncode != 0:
        err = result.stderr.strip()
        if "CONFLICT" in err or "merge" in err.lower():
            print(f"ERROR: merge conflict during pull — resolve manually: {err}", file=sys.stderr)
            sys.exit(1)
        print(f"ERROR: git pull failed: {err}", file=sys.stderr)
        sys.exit(1)
    pull_cache.write_text(str(time.time()))


def git_commit_and_push(message: str) -> None:
    git_run("add", "-A")
    result = git_run("commit", "-m", message, check=False)
    if result.returncode != 0 and "nothing to commit" not in result.stdout:
        print(f"ERROR: git commit failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    result = git_run("push", check=False)
    if result.returncode != 0:
        print(f"ERROR: git push failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)


def cmd_list(folder: str) -> None:
    ensure_vault()
    target = VAULT_DIR / folder
    if not target.exists():
        print(json.dumps([]))
        return
    paths = sorted(
        str(p.relative_to(VAULT_DIR))
        for p in target.rglob("*.md")
        if not p.name.startswith(".")
    )
    print(json.dumps(paths))


def cmd_read(path: str) -> None:
    ensure_vault()
    note = VAULT_DIR / path
    if not note.exists():
        print(f"ERROR: note not found: {path}", file=sys.stderr)
        sys.exit(1)
    print(note.read_text())


def cmd_write(path: str, content: str) -> None:
    check_write_allowed(path)
    lock_path = VAULT_DIR / ".hermes.lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        ensure_vault()
        note = VAULT_DIR / path
        note.parent.mkdir(parents=True, exist_ok=True)
        note.write_text(content)
        git_commit_and_push(f"chore(hermes): write {path}")
    print(f"OK: wrote {path}")


def cmd_append(path: str, content: str) -> None:
    check_write_allowed(path)
    lock_path = VAULT_DIR / ".hermes.lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        ensure_vault()
        note = VAULT_DIR / path
        note.parent.mkdir(parents=True, exist_ok=True)
        existing = note.read_text() if note.exists() else ""
        separator = "\n" if existing and not existing.endswith("\n") else ""
        note.write_text(existing + separator + content)
        git_commit_and_push(f"chore(hermes): append {path}")
    print(f"OK: appended to {path}")


def cmd_search(query: str) -> None:
    ensure_vault()
    result = subprocess.run(
        ["grep", "-rl", "--include=*.md", query, str(VAULT_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        print(f"ERROR: search failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    matches = [
        str(Path(line).relative_to(VAULT_DIR))
        for line in result.stdout.splitlines()
        if line
    ]
    print(json.dumps(matches))


def main() -> None:
    parser = argparse.ArgumentParser(description="Obsidian vault CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List .md files in a folder")
    p_list.add_argument("folder")

    p_read = sub.add_parser("read", help="Print note content")
    p_read.add_argument("path")

    p_write = sub.add_parser("write", help="Overwrite a note")
    p_write.add_argument("path")
    p_write.add_argument("content")

    p_append = sub.add_parser("append", help="Append to a note")
    p_append.add_argument("path")
    p_append.add_argument("content")

    p_search = sub.add_parser("search", help="Search notes by text")
    p_search.add_argument("query")

    args = parser.parse_args()

    if args.cmd == "list":
        cmd_list(args.folder)
    elif args.cmd == "read":
        cmd_read(args.path)
    elif args.cmd == "write":
        cmd_write(args.path, args.content)
    elif args.cmd == "append":
        cmd_append(args.path, args.content)
    elif args.cmd == "search":
        cmd_search(args.query)


if __name__ == "__main__":
    main()
