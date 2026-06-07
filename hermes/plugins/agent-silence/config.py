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

    DOER_URL stays graceful: the doer integration is optional/pluggable
    (the plugin separately scans for *any* AGENT_*_URL var in _load_config),
    so a missing doer service should disable that one feature, not crash
    the gateway in environments that don't run it.
    """

    TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
    DOER_URL: str = os.environ.get("AGENT_DOER_URL", "")


CONFIG = Config()
