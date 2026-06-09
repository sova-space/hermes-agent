"""Hermes credential registry — env var definitions and .env I/O helpers.

This module has NO side effects on import. Both server.py (admin UI) and
infra/bootstrap_env.py (container boot) import from here so the authoritative
list of supported credentials lives in exactly one place.
"""

from pathlib import Path

# (key, label, category, is_secret)
ENV_VARS: list[tuple[str, str, str, bool]] = [
    ("LLM_MODEL",   "Model (gateway / Q&A)",      "model", False),
    ("AGENT_MODEL", "Agent model (code writing)", "model", False),
    ("QUICK_MODEL", "Quick model (lint / ops)",   "model", False),
    ("NOUS_API_KEY", "Nous Research", "provider", True),
    ("OPENROUTER_API_KEY", "OpenRouter", "provider", True),
    ("DEEPSEEK_API_KEY", "DeepSeek", "provider", True),
    ("DASHSCOPE_API_KEY", "Qwen Cloud (DashScope)", "provider", True),
    ("GLM_API_KEY", "GLM / Z.AI", "provider", True),
    ("KIMI_API_KEY", "Kimi", "provider", True),
    ("MINIMAX_API_KEY", "MiniMax", "provider", True),
    ("HF_TOKEN", "Hugging Face", "provider", True),
    ("NVIDIA_API_KEY", "NVIDIA NIM", "provider", True),
    ("ARCEE_API_KEY", "Arcee AI", "provider", True),
    ("STEPFUN_API_KEY", "Step Plan", "provider", True),
    ("AI_GATEWAY_API_KEY", "Vercel AI Gateway", "provider", True),
    ("GEMINI_API_KEY", "Google AI Studio", "provider", True),
    ("NOVITA_API_KEY", "NovitaAI", "provider", True),
    ("FIREWORKS_API_KEY", "Fireworks AI", "provider", True),
    ("CUSTOM_PROVIDER_API_KEY", "Custom Provider key", "provider", True),
    ("CUSTOM_PROVIDER_BASE_URL", "Custom Provider base URL", "custom", False),
    ("CUSTOM_PROVIDER_NAME", "Custom Provider name", "custom", False),
    ("PARALLEL_API_KEY", "Parallel (search)", "tool", True),
    ("FIRECRAWL_API_KEY", "Firecrawl (scrape)", "tool", True),
    ("TAVILY_API_KEY", "Tavily (search)", "tool", True),
    ("FAL_KEY", "FAL (image gen)", "tool", True),
    ("BROWSERBASE_API_KEY", "Browserbase key", "tool", True),
    ("BROWSERBASE_PROJECT_ID", "Browserbase project", "tool", False),
    ("GITHUB_TOKEN", "GitHub token", "tool", True),
    ("VOICE_TOOLS_OPENAI_KEY", "OpenAI (voice/TTS)", "tool", True),
    ("HONCHO_API_KEY", "Honcho (memory)", "tool", True),
    ("TELEGRAM_BOT_TOKEN", "Bot Token", "telegram", True),
    ("TELEGRAM_ALLOWED_USERS", "Allowed User IDs", "telegram", False),
    ("DISCORD_BOT_TOKEN", "Bot Token", "discord", True),
    ("DISCORD_ALLOWED_USERS", "Allowed User IDs", "discord", False),
    ("SLACK_BOT_TOKEN", "Bot Token (xoxb-...)", "slack", True),
    ("SLACK_APP_TOKEN", "App Token (xapp-...)", "slack", True),
    ("WHATSAPP_ENABLED", "Enable WhatsApp", "whatsapp", False),
    ("EMAIL_ADDRESS", "Email Address", "email", False),
    ("EMAIL_PASSWORD", "Email Password", "email", True),
    ("EMAIL_IMAP_HOST", "IMAP Host", "email", False),
    ("EMAIL_SMTP_HOST", "SMTP Host", "email", False),
    ("MATTERMOST_URL", "Server URL", "mattermost", False),
    ("MATTERMOST_TOKEN", "Bot Token", "mattermost", True),
    ("MATRIX_HOMESERVER", "Homeserver URL", "matrix", False),
    ("MATRIX_ACCESS_TOKEN", "Access Token", "matrix", True),
    ("MATRIX_USER_ID", "User ID", "matrix", False),
    ("GATEWAY_ALLOW_ALL_USERS", "Allow all users", "gateway", False),
    ("ADMIN_USERNAME", "Admin username", "admin", False),
    ("ADMIN_PASSWORD", "Admin password", "admin", True),
]

SECRET_KEYS: frozenset[str] = frozenset(k for k, _, _, s in ENV_VARS if s)
PROVIDER_KEYS: list[str] = [k for k, _, c, _ in ENV_VARS if c == "provider"]
CHANNEL_MAP: dict[str, str] = {
    "Telegram": "TELEGRAM_BOT_TOKEN",
    "Discord": "DISCORD_BOT_TOKEN",
    "Slack": "SLACK_BOT_TOKEN",
    "WhatsApp": "WHATSAPP_ENABLED",
    "Email": "EMAIL_ADDRESS",
    "Mattermost": "MATTERMOST_TOKEN",
    "Matrix": "MATRIX_ACCESS_TOKEN",
}

_CAT_ORDER = [
    "model", "provider", "tool", "telegram", "discord",
    "slack", "whatsapp", "email", "mattermost", "matrix", "gateway",
]
_CAT_LABELS = {
    "model": "Model", "provider": "Providers", "tool": "Tools",
    "telegram": "Telegram", "discord": "Discord", "slack": "Slack",
    "whatsapp": "WhatsApp", "email": "Email", "mattermost": "Mattermost",
    "matrix": "Matrix", "gateway": "Gateway",
}
_KEY_CAT: dict[str, str] = {k: c for k, _, c, _ in ENV_VARS}


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        out[k.strip()] = v
    return out


def write_env(path: Path, data: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[str]] = {c: [] for c in _CAT_ORDER}
    grouped["other"] = []

    for k, v in data.items():
        if not v:
            continue
        cat = _KEY_CAT.get(k, "other")
        grouped.setdefault(cat, []).append(f"{k}={v}")

    lines: list[str] = []
    for cat in _CAT_ORDER:
        entries = sorted(grouped.get(cat, []))
        if entries:
            lines.append(f"# {_CAT_LABELS.get(cat, cat)}")
            lines.extend(entries)
            lines.append("")
    if grouped["other"]:
        lines.append("# Other")
        lines.extend(sorted(grouped["other"]))
        lines.append("")

    path.write_text("\n".join(lines))
