import os

import httpx

_agent_commands: set[str] = set()
_doer_projects: list[str] = []
_config_loaded = False

# Commands Hermes routes to the Doer agent: do_<project>
_DOER_PREFIX = "do_"

# In-memory project context per chat: {chat_id: project_name}
_selected_projects: dict[int, str] = {}

# Chat IDs awaiting a project selection button tap
_pending_selection: set[int] = set()


def _load_config() -> None:
    global _config_loaded
    if _config_loaded:
        return

    urls = [
        v
        for k, v in os.environ.items()
        if k.startswith("AGENT_") and k.endswith("_URL")
    ]
    for base_url in urls:
        url = base_url.rstrip("/")
        if not url.startswith("http"):
            url = f"https://{url}"
        try:
            resp = httpx.get(f"{url}/bot/commands", timeout=5)
            _agent_commands.update(c["command"] for c in resp.json())
        except Exception:
            pass
        try:
            resp = httpx.get(f"{url}/bot/projects", timeout=5)
            projects = resp.json()
            if isinstance(projects, list):
                _doer_projects.extend(p for p in projects if isinstance(p, str))
        except Exception:
            pass

    _config_loaded = True


def _get_projects() -> list[str]:
    """Return the doer project list, loading it if not yet fetched."""
    _load_config()
    return _doer_projects


def _get_chat_and_thread(event) -> tuple[int | None, int | None]:
    chat_id = (
        getattr(event, "chat_id", None)
        or getattr(getattr(event, "chat", None), "id", None)
        or getattr(getattr(event, "message", None), "chat", {}).get("id")
    )
    thread_id = (
        getattr(event, "message_thread_id", None)
        or getattr(getattr(event, "message", None), "message_thread_id", None)
    )
    return chat_id, thread_id


def _send_telegram_message(
    chat_id: int,
    thread_id: int | None,
    text: str,
    reply_markup: dict | None = None,
) -> None:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token or not chat_id:
        return
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if thread_id:
        payload["message_thread_id"] = thread_id
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    try:
        httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json=payload,
            timeout=5,
        )
    except Exception:
        pass


def _dispatch_doer(chat_id: int, thread_id: int | None, project: str, task: str) -> None:
    if not task:
        return

    doer_url = os.environ.get("AGENT_DOER_URL", "").rstrip("/")
    if doer_url:
        try:
            httpx.post(f"{doer_url}/task", json={"project": project, "task": task}, timeout=5)
        except Exception:
            pass

    _send_telegram_message(
        chat_id,
        thread_id,
        f"Got it — Doer is working on `{project}`. Result in #projects.",
    )


def pre_dispatch(event, **kwargs):
    _load_config()

    text = getattr(event, "text", "") or ""
    cmd = event.get_command() if hasattr(event, "get_command") else None
    chat_id, thread_id = _get_chat_and_thread(event)

    # Handle project selection from keyboard tap (plain text, no command)
    if cmd is None and chat_id is not None and chat_id in _pending_selection:
        chosen = text.strip().lower()
        if chosen in _get_projects():
            _pending_selection.discard(chat_id)
            _selected_projects[chat_id] = chosen
            _send_telegram_message(
                chat_id,
                thread_id,
                f"Project set to *{chosen}*. Use `/do <task>` to run a task.",
                reply_markup={"remove_keyboard": True},
            )
            return {"action": "skip", "reason": "doer project selected"}

    if not cmd:
        return None

    # /project — show project picker keyboard
    if cmd == "project":
        projects = _get_projects()
        if not projects:
            _send_telegram_message(chat_id, thread_id, "Doer is unavailable — no projects loaded.")
            return {"action": "skip", "reason": "doer project picker unavailable"}
        _pending_selection.add(chat_id)
        buttons = [[{"text": p.capitalize()} for p in projects]]
        _send_telegram_message(
            chat_id,
            thread_id,
            "Select a project:",
            reply_markup={"keyboard": buttons, "one_time_keyboard": True, "resize_keyboard": True},
        )
        return {"action": "skip", "reason": "doer project picker"}

    # /do <task> — dispatch to stored project
    if cmd == "do":
        project = _selected_projects.get(chat_id) if chat_id else None
        if not project:
            _send_telegram_message(
                chat_id,
                thread_id,
                "No project selected. Use `/project` to pick one first.",
            )
            return {"action": "skip", "reason": "no doer project selected"}
        parts = text.split(None, 1)
        task = parts[1].strip() if len(parts) > 1 else ""
        if not task:
            _send_telegram_message(
                chat_id,
                thread_id,
                f"Active project: *{project}*. Usage: `/do <task description>`",
            )
            return {"action": "skip", "reason": "doer no task"}
        _dispatch_doer(chat_id, thread_id, project, task)
        return {"action": "skip", "reason": "doer command"}

    # /do_<project> <task> — explicit project, also updates stored project
    if cmd.startswith(_DOER_PREFIX):
        project = cmd[len(_DOER_PREFIX):]
        if chat_id is not None:
            _selected_projects[chat_id] = project
        parts = text.split(None, 1)
        task = parts[1].strip() if len(parts) > 1 else ""
        if not task:
            return {"action": "skip", "reason": "doer no task"}
        _dispatch_doer(chat_id, thread_id, project, task)
        return {"action": "skip", "reason": "doer command"}

    # Silence commands owned by other bots (only when @-addressed).
    if cmd not in _agent_commands:
        return None
    command_token = text.split()[0] if text else ""
    if "@" in command_token:
        return {"action": "skip", "reason": "agent bot command"}
    return None


def _cmd_project(raw_args: str) -> str:
    projects = _get_projects()
    return "Projects: " + ", ".join(projects) if projects else "No projects loaded."


def _cmd_do(raw_args: str) -> str:
    return "Usage: /do <task description>"


def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", pre_dispatch)
    ctx.register_command("project", handler=_cmd_project, description="Pick active project for Doer")
    ctx.register_command("do", handler=_cmd_do, description="Run task on active project via Doer", args_hint="<task>")
    _load_config()
