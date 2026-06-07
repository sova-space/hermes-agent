"""Discovery of, and dispatch to, Doer-capable agent services.

Hermes exposes registered agent services through ``AGENT_*_URL`` env vars — a
dynamic, unbounded set (hence the prefix scan rather than a fixed config key;
see ``Config`` in ``config.py`` for why that can't live in the dataclass).
Each one may expose:

- ``GET /bot/commands`` — slash commands that agent owns, so this plugin can
  silence @-addressed duplicates Hermes would otherwise reply "unknown" to.
- ``GET /bot/projects`` — project names the Doer can run tasks against.

``DoerGateway`` owns that discovery plus posting tasks to the Doer's
dispatch endpoint. ``DoerSession`` separately tracks each chat's active
project and pending-selection state — that's per-conversation memory, not
service discovery, hence the split.
"""

import os
from dataclasses import dataclass, field

import httpx

# Env var prefix/suffix this plugin scans for agent base URLs, e.g.
# AGENT_DOER_URL, AGENT_RESEARCH_URL, ... Anything matching is probed.
_AGENT_URL_PREFIX = "AGENT_"
_AGENT_URL_SUFFIX = "_URL"


class DoerGateway:
    """Lazily discovers agent commands/projects, and dispatches Doer tasks."""

    def __init__(self, dispatch_url: str):
        self._dispatch_url = dispatch_url.rstrip("/")
        self._loaded = False
        self.agent_commands: set[str] = set()
        self.projects: list[str] = []

    def load(self) -> None:
        """Discover agent commands and Doer projects once, lazily.

        Cheap to call on every dispatch — it's a no-op after the first
        successful pass, mirroring how the rest of the gateway treats
        per-process config (load-once, cache for the process lifetime).
        """
        if self._loaded:
            return
        for base_url in self._discover_agent_urls():
            url = self._normalize(base_url)
            self._load_commands(url)
            self._load_projects(url)
        self._loaded = True

    def dispatch(self, project: str, task: str) -> None:
        """POST a task to the Doer's dispatch endpoint, swallowing errors —
        the user-visible confirmation is sent separately by the caller."""
        if not self._dispatch_url:
            return
        try:
            httpx.post(
                f"{self._dispatch_url}/task",
                json={"project": project, "task": task},
                timeout=5,
            )
        except Exception:
            pass

    @staticmethod
    def _discover_agent_urls() -> list[str]:
        return [
            v
            for k, v in os.environ.items()
            if k.startswith(_AGENT_URL_PREFIX) and k.endswith(_AGENT_URL_SUFFIX)
        ]

    @staticmethod
    def _normalize(base_url: str) -> str:
        url = base_url.rstrip("/")
        return url if url.startswith("http") else f"https://{url}"

    def _load_commands(self, url: str) -> None:
        try:
            resp = httpx.get(f"{url}/bot/commands", timeout=5)
            self.agent_commands.update(c["command"] for c in resp.json())
        except Exception:
            pass

    def _load_projects(self, url: str) -> None:
        try:
            resp = httpx.get(f"{url}/bot/projects", timeout=5)
            projects = resp.json()
            if isinstance(projects, list):
                self.projects.extend(p for p in projects if isinstance(p, str))
        except Exception:
            pass


@dataclass
class DoerSession:
    """Per-chat Doer state: which project is active, and whether the chat is
    waiting on a keyboard-tap project selection.

    Keyed by ``ChatContext.chat_id`` (a string — see ``chat_context.py`` for
    why that matters: it's the same id Telegram's *string* ``SessionSource``
    carries, not a raw integer).
    """

    _active_project: dict[str, str] = field(default_factory=dict)
    _awaiting_selection: set[str] = field(default_factory=set)

    def active_project(self, chat_id: str | None) -> str | None:
        return self._active_project.get(chat_id) if chat_id else None

    def select(self, chat_id: str, project: str) -> None:
        """Record ``project`` as active for ``chat_id`` and clear any pending
        picker state — used both by the keyboard-tap flow and the
        ``/do_<project>`` shorthand."""
        self._awaiting_selection.discard(chat_id)
        self._active_project[chat_id] = project

    def await_selection(self, chat_id: str) -> None:
        self._awaiting_selection.add(chat_id)

    def is_awaiting_selection(self, chat_id: str | None) -> bool:
        return chat_id is not None and chat_id in self._awaiting_selection
