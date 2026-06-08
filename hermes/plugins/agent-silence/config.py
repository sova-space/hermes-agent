"""Environment-derived configuration for the agent-silence plugin."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Single source of truth for the env vars this plugin reads.

    TELEGRAM_BOT_TOKEN is fail-loud: this plugin runs inside the Hermes
    gateway, which IS a Telegram bot — booting without a token is already
    broken, so surface that at import time rather than failing silently
    on every Telegram call.

    GITHUB_TOKEN / OPENROUTER_API_KEY / DEVOPS_MODEL back the absorbed devops
    loop (formerly Doer's own service — see ``devops.py``). OPENROUTER_API_KEY
    is shared with Hermes's own LLM provider config (``server.py``'s env
    registry already lists it) — no separate credential needed. DEVOPS_MODEL
    defaults to a Haiku-class model: devops tasks are mostly file reads/writes
    and tool-call plumbing, not deep reasoning, so the cheaper model is the
    right default for routine code-change loops.
    """

    TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
    GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
    OPENROUTER_API_KEY: str = os.environ.get("OPENROUTER_API_KEY", "")
    DEVOPS_MODEL: str = os.environ.get("DEVOPS_MODEL", "anthropic/claude-haiku-4.5")


CONFIG = Config()
