"""Discovery of, and dispatch to, Doer-capable agent services.

Hermes exposes registered agent services through ``AGENT_*_URL`` env vars — a
dynamic, unbounded set (hence the prefix scan rather than a fixed config key;
see ``Config`` in ``config.py`` for why that can't live in the dataclass).
Each one may expose:

- ``GET /bot/commands`` — slash commands that agent owns, so this plugin can
  silence @-addressed duplicates Hermes would otherwise reply "unknown" to.
- ``GET /bot/projects`` — project names the Doer can run devops tasks against.
- ``GET /bot/profile`` — domain-Q&A registration: ``{name, description,
  dispatch_path}``. A bot that owns a profile (e.g. ``finance``) answers
  free-form questions at ``{base_url}{dispatch_path}`` — see ``ask_profile``.

``DoerGateway`` owns that discovery plus dispatching: devops tasks to the
Doer, domain questions to the profile-owning bot's assistant. ``DoerSession``
separately tracks each chat's active profile and pending-selection state —
that's per-conversation memory, not service discovery, hence the split.

Two distinct things route two different ways once a profile is active (see
``specs/014-profile-router/spec.md``):

- ``/do <task>`` (explicit devops verb) → ``dispatch`` → Doer's generic
  GitHub loop, scoped to the profile's repo
- a plain-text message → ``ask_profile`` → the profile-owning bot's own
  conversational assistant, if one is registered; otherwise falls through
  to ordinary Hermes conversation (no domain owner to ask)
"""

import os
from dataclasses import dataclass, field

import httpx

# Env var prefix/suffix this plugin scans for agent base URLs, e.g.
# AGENT_DOER_URL, AGENT_RESEARCH_URL, ... Anything matching is probed.
_AGENT_URL_PREFIX = "AGENT_"
_AGENT_URL_SUFFIX = "_URL"


@dataclass(frozen=True)
class ProfileOwner:
    """A registered domain-Q&A owner, as discovered via ``GET /bot/profile``."""

    base_url: str
    description: str
    dispatch_path: str


class DoerGateway:
    """Lazily discovers agent commands/projects/profiles, dispatches devops
    tasks to the Doer, and routes domain Q&A to profile owners."""

    def __init__(self, dispatch_url: str):
        self._dispatch_url = dispatch_url.rstrip("/")
        self._loaded = False
        self.agent_commands: set[str] = set()
        self.projects: list[str] = []
        self.profiles: dict[str, ProfileOwner] = {}

    def load(self) -> None:
        """Discover agent commands, Doer projects, and profile owners once,
        lazily.

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
            self._load_profile(url)
        self._loaded = True

    def dispatch(self, project: str, task: str) -> None:
        """POST a devops task to the Doer's dispatch endpoint, swallowing
        errors — the user-visible confirmation is sent separately by the
        caller."""
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

    def ask_profile(self, profile: str, chat_id: str, text: str) -> str | None:
        """POST a domain question to the profile owner's assistant.

        Returns the assistant's reply, or ``None`` when no owner is
        registered for ``profile`` or the call fails — the caller treats
        ``None`` as "let this fall through to ordinary conversation",
        not an error to surface.
        """
        owner = self.profiles.get(profile)
        if owner is None:
            return None
        try:
            resp = httpx.post(
                f"{owner.base_url}{owner.dispatch_path}",
                json={"chat_id": int(chat_id), "text": text},
                timeout=60,
            )
            resp.raise_for_status()
            reply = resp.json().get("reply")
            return reply if isinstance(reply, str) else None
        except Exception:
            return None

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

    def _load_profile(self, url: str) -> None:
        try:
            resp = httpx.get(f"{url}/bot/profile", timeout=5)
            data = resp.json()
            name = data.get("name")
            dispatch_path = data.get("dispatch_path")
            if isinstance(name, str) and isinstance(dispatch_path, str):
                self.profiles[name] = ProfileOwner(
                    base_url=url,
                    description=data.get("description", ""),
                    dispatch_path=dispatch_path,
                )
        except Exception:
            pass


@dataclass
class DoerSession:
    """Per-chat state: which profile is active.

    Once a chat has an active profile, ``/do <task>`` runs a devops task
    against that profile's repo, and plain-text messages (no leading ``/``)
    go to the profile owner's conversational assistant (if one is
    registered) — see ``commands.handle_devops_task`` and
    ``commands.handle_profile_message``. Keyed by ``ChatContext.chat_id``
    (a string — see ``chat_context.py`` for why that matters: it's the same
    id Telegram's *string* ``SessionSource`` carries, not a raw integer).
    """

    _active_profile: dict[str, str] = field(default_factory=dict)

    def active_profile(self, chat_id: str | None) -> str | None:
        return self._active_profile.get(chat_id) if chat_id else None

    def select(self, chat_id: str, profile: str) -> None:
        self._active_profile[chat_id] = profile
