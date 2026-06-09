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

    GITHUB_TOKEN / NOUS_API_KEY / AGENT_MODEL / QUICK_MODEL back the absorbed
    devops loop (formerly Doer's own service — see ``agent_loop.py``). NOUS_API_KEY
    authenticates against the Nous Research inference API (OpenAI-compatible).
    The dev loop uses two models: AGENT_MODEL for code writing, QUICK_MODEL for
    mechanical ops like file reads, git diff analysis, and PR creation.
    """

    TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
    GITHUB_TOKEN: str = os.environ.get("GITHUB_TOKEN", "")
    NOUS_API_KEY: str = os.environ.get("NOUS_API_KEY", "")
    # AGENT_MODEL handles code writing and architectural decisions in the dev loop.
    # QUICK_MODEL handles mechanical work: file reads, git diff, PR creation — saving
    # tokens on turns that don't need deep reasoning.
    AGENT_MODEL: str = os.environ.get("AGENT_MODEL", "anthropic/claude-sonnet-4-5")
    QUICK_MODEL: str = os.environ.get("QUICK_MODEL", "anthropic/claude-haiku-4-5")


CONFIG = Config()
