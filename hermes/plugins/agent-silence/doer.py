"""Discovery of profile owners, and routing of domain Q&A to them.

Hermes exposes registered agent services through ``AGENT_*_URL`` env vars — a
dynamic, unbounded set (hence the prefix scan rather than a fixed config key;
see ``Config`` in ``config.py`` for why that can't live in the dataclass).
Each one may expose:

- ``GET /bot/commands`` — slash commands that agent owns, so this plugin can
  silence @-addressed duplicates Hermes would otherwise reply "unknown" to.
- ``GET /bot/profile`` — domain-Q&A registration: ``{name, description,
  dispatch_path}``. A bot that owns a profile (e.g. ``finance``) answers
  free-form questions at ``{base_url}{dispatch_path}`` — see ``ask_profile``.

``DoerGateway`` owns that discovery plus routing domain questions to the
profile-owning bot's assistant. ``DoerSession`` separately tracks each chat's
active profile *and* mode — that's per-conversation memory, not service
discovery, hence the split.

Devops dispatch no longer lives here: per spec 014 step 2 ("absorb Doer"),
the generic GitHub loop now runs in-process — see ``agent_loop.AgentLoop``. The
profile list is the local ``agent_loop.PROJECTS`` registry directly; there is no
``GET /bot/projects`` to discover anymore (that contract retired with the
standalone Doer service).

Two distinct things route two different ways once a profile is active, now
governed by the chat's *mode* (``/mode client|dev`` — see
``specs/014-profile-router/spec.md`` for the original design, since evolved
from the per-message ``/do``-vs-plain-text split to a sticky toggle):

- *dev* mode → ``AgentLoop.dispatch`` → the absorbed GitHub loop, scoped to
  the profile's repo
- *client* mode → ``ask_profile`` → the profile-owning bot's own
  conversational assistant, if one is registered; otherwise falls through
  to ordinary Hermes conversation (no domain owner to ask)
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .agent_loop import PROJECTS

# Env var prefix/suffix this plugin scans for agent base URLs, e.g.
# AGENT_FINANCE_URL, AGENT_RESEARCH_URL, ... Anything matching is probed.
_AGENT_URL_PREFIX = "AGENT_"
_AGENT_URL_SUFFIX = "_URL"


@dataclass(frozen=True)
class ProfileOwner:
    """A registered domain-Q&A owner, as discovered via ``GET /bot/profile``."""

    base_url: str
    description: str
    dispatch_path: str


class DoerGateway:
    """Lazily discovers agent commands and profile owners, and routes domain
    Q&A to them. Profiles themselves come from the local ``PROJECTS``
    registry — no remote discovery needed now that devops runs in-process."""

    def __init__(self):
        self._loaded = False
        self.agent_commands: set[str] = set()
        self.projects: list[str] = sorted(PROJECTS)
        self.profiles: dict[str, ProfileOwner] = {}
        self.llm_model = os.environ.get("LLM_MODEL", "unknown")
        self.agent_model = os.environ.get("AGENT_MODEL", "unknown")
        self.quick_model = os.environ.get("QUICK_MODEL", "unknown")

    def load(self) -> None:
        """Discover agent commands and profile owners once, lazily.

        Cheap to call on every dispatch — it's a no-op after the first
        successful pass, mirroring how the rest of the gateway treats
        per-process config (load-once, cache for the process lifetime).
        """
        if self._loaded:
            return
        for base_url in self._discover_agent_urls():
            url = self._normalize(base_url)
            self._load_commands(url)
            self._load_profile(url)
        self._loaded = True

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


# Mode names — the explicit, sticky signal that replaced the old
# /do-vs-plain-text per-message split (see module docstring + commands.py).
# CLIENT is the default: the safer no-op mode to land a chat in (asking a
# question can't accidentally kick off a GitHub-editing loop).
MODE_CLIENT = "client"
MODE_DEV = "dev"
MODES = (MODE_CLIENT, MODE_DEV)


# Shared with infra/patch_telegram_finance_callbacks.py so gateway-level inline
# callbacks and this plugin see the same active profile/mode state.
_SESSION_STATE_PATH = (
    Path(os.environ.get("HERMES_HOME", "/data/.hermes")) / "agent-silence-session.json"
)


@dataclass
class DoerSession:
    """Per-chat state: which profile is active, and in which mode.

    Once a chat has an active profile, its *mode* decides how plain-text
    messages route — ``client`` to the profile owner's conversational
    assistant, ``dev`` to the absorbed devops loop scoped to that profile's
    repo (see ``commands.handle_profile_message``). Mode is sticky and
    explicit by design: switching modes IS signalling intent, so routing
    never has to guess "is this a question or a task" from an LLM's read of
    the message — exactly the ambiguity spec 014 called out as dangerous to
    infer. Keyed by ``ChatContext.chat_id`` (a string — see ``chat_context.py``
    for why that matters: it's the same id Telegram's *string* ``SessionSource``
    carries, not a raw integer).
    """

    _active_profile: dict[str, str] = field(default_factory=dict)
    _active_mode: dict[str, str] = field(default_factory=dict)

    def _load(self) -> None:
        try:
            data = json.loads(_SESSION_STATE_PATH.read_text())
        except Exception:
            return
        profiles = data.get("active_profile")
        modes = data.get("active_mode")
        if isinstance(profiles, dict):
            self._active_profile = {
                str(k): str(v) for k, v in profiles.items() if isinstance(v, str)
            }
        if isinstance(modes, dict):
            self._active_mode = {str(k): str(v) for k, v in modes.items() if v in MODES}

    def _save(self) -> None:
        try:
            _SESSION_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = _SESSION_STATE_PATH.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(
                    {
                        "active_profile": self._active_profile,
                        "active_mode": self._active_mode,
                    },
                    sort_keys=True,
                )
            )
            tmp.replace(_SESSION_STATE_PATH)
        except Exception:
            pass

    def active_profile(self, chat_id: str | None) -> str | None:
        self._load()
        return self._active_profile.get(chat_id) if chat_id else None

    def select(self, chat_id: str, profile: str) -> None:
        self._load()
        self._active_profile[chat_id] = profile
        self._active_mode.setdefault(chat_id, MODE_CLIENT)
        self._save()

    def active_mode(self, chat_id: str | None) -> str:
        self._load()
        if chat_id is None:
            return MODE_CLIENT
        return self._active_mode.get(chat_id, MODE_CLIENT)

    def set_mode(self, chat_id: str, mode: str) -> None:
        self._load()
        self._active_mode[chat_id] = mode
        self._save()
