# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Single-file Python admin server (`server.py`) that manages and reverse-proxies the upstream [Hermes Agent](https://github.com/nousresearch/hermes) gateway and dashboard. Designed for one-click Railway deployment with persistent config on a Docker volume.

## Development Workflow

Development is Docker-only — there is no local Python virtualenv workflow.

Dependencies are managed with `uv`. After editing `pyproject.toml`, regenerate the lockfile:
```
uv lock
```

**Build:**
```
docker build -t hermes-agent .
```

**Run locally:**
```
docker run --rm -it -p 8080:8080 -e PORT=8080 -e ADMIN_PASSWORD=changeme -v hermes-data:/data hermes-agent
```

There are no automated tests. Verify changes by building the image and exercising the relevant UI flows manually.

## Upgrading Hermes

To update the upstream Hermes version, manually bump `HERMES_REF` in the `Dockerfile` (currently pinned to a version tag like `v2026.5.16`), then rebuild the Docker image. See `/upgrade-hermes` for the full workflow.

## Branch Conventions

Use `feature/<name>` for new work and `fix/<name>` for bug fixes.

## Required Environment Variables

Core (always set):
- `PORT` — web server port (default 8080)
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` — basic auth (password auto-generated and logged if unset)
- At least one LLM provider key: `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, etc.
- `LLM_MODEL` — model identifier (e.g., `openai/gpt-4o-mini`, `claude-sonnet-4-5`)

Data must persist via a Docker volume mounted at `/data`.

## Critical Gotchas

**Zombie process reaping**: The container uses `tini` as PID 1. Do not remove it — Hermes spawns git, bun, and browser subprocesses, and without tini the PID table exhausts over time ("fork: cannot allocate memory").

**Cookie-based auth**: The admin server uses HMAC-signed cookies instead of Basic Auth headers (SPA `fetch()` doesn't reliably pass auth headers cross-browser). The cookie signing secret regenerates on every process start, so redeploying invalidates all sessions.

**PID file race**: `start.sh` unconditionally removes `/data/.hermes/gateway.pid` on boot. The Docker volume survives container restarts and Hermes doesn't clean up its PID file on SIGTERM — leaving it causes hermes to refuse to start.

**Pre-built TUI**: The React dashboard and terminal UI (`ui-tui`) are compiled at Docker image build time (not runtime). `HERMES_TUI_DIR=/opt/hermes-agent/ui-tui` tells hermes where to find the pre-built bundle. Do not move or delete these during image builds.

**Config deep-merge**: On startup, `server.py` deep-merges into `/data/.hermes/config.yaml` and `/data/.hermes/.env` without overwriting keys already set by the user (MCP servers, cron config, custom skills). Do not replace these files wholesale — use deep-merge helpers already in the codebase.

**Reverse proxy headers**: The proxy strips hop-by-hop headers but intentionally preserves `Authorization` and `Cookie` — the Hermes dashboard relies on them. Do not strip these.

<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan
<!-- SPECKIT END -->
