#!/usr/bin/env python3
"""Bootstrap $HERMES_HOME/.env from process env vars on every container start.

The hermes gateway reads credentials from $HERMES_HOME/.env (the file the
admin UI writes on first setup). After a volume wipe or a fresh deploy with
no prior setup, that file is empty — so the gateway starts with no Telegram
token, no LLM provider key, etc., and the bot silently does nothing.

This script re-writes .env from the current process env vars on every boot,
using write_env() from hermes.env_registry — the same format the admin UI
produces. The result is a self-healing credential file: always rebuilt from
Railway's authoritative vars, never left stale or empty after a wipe.

Runs before `python /app/server.py` in start.sh so the gateway sees a fully
populated .env from the first request.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, "/app")
from hermes.env_registry import ENV_VARS, write_env  # noqa: E402

hermes_home = os.environ.get("HERMES_HOME", "/data/.hermes")
env_path = Path(hermes_home) / ".env"

data = {key: val for key, _, _, _ in ENV_VARS if (val := os.environ.get(key, ""))}
write_env(env_path, data)
print(f"[bootstrap] wrote {len(data)} credential(s) to {env_path}", flush=True)
