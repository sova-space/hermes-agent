"""Built-in devops capability — Doer's generic GitHub agent loop, absorbed.

Doer used to run as a standalone Railway service with its own bot identity
(``DOER_BOT_TOKEN``) purely to post results to ``#projects``. Per spec 014's
staged plan ("router first, absorption second"), that loop carried no domain
logic — it was generic, parameterized only by ``PROJECTS[name].repo`` — so
folding it into Hermes doesn't violate the bot-independence rule (that rule
protects *domain* logic, not generic infrastructure). Now Hermes posts the
results itself, through its own ``TelegramClient`` — no second bot needed.

Runs on a background **thread**, not ``asyncio``: plugins execute inside the
shared Hermes gateway process from a synchronous ``pre_gateway_dispatch``
hook (see ``__init__.py``), with no guaranteed access to a running event
loop — and "only ``httpx``/stdlib available" (see ``telegram_client.py``)
ruled out reaching for an async GitHub client. ``threading.Thread`` is the
dependency-free way to fire a long multi-round-trip loop without blocking
the hook that triggered it; the original async tool implementations
(``bots/doer/doer_api/agent/tools.py``) are mirrored here as sync ``httpx``
calls for that reason.
"""

import base64
import logging
import threading
from dataclasses import dataclass
from typing import TypedDict

import anthropic
import httpx

from .chat_context import ChatContext
from .telegram_client import TelegramClient

# stdlib logging, not structlog: structlog is a dependency of the standalone
# bot services (finance/wishlist/doer's own pyproject.toml extras) but isn't
# installed in the Hermes gateway runtime this plugin loads into (checked
# uv.lock and infra/Dockerfile's install extras — absent from both). Importing
# it here would crash plugin load with ModuleNotFoundError.
log = logging.getLogger(__name__)

_GITHUB_API_URL = "https://api.github.com"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Where devops results land — same #projects topic Doer posted to
# (`bots/doer/.env.example`'s TELEGRAM_CHAT_ID / TELEGRAM_PROJECTS_TOPIC_ID).
_PROJECTS_CHAT = ChatContext(chat_id="-1003913424869", thread_id="167")


class Project(TypedDict):
    """GitHub project target."""

    repo: str
    base_branch: str


# Moved verbatim from bots/doer/doer_api/agent/projects.py — must keep these
# slugs in sync with project-context's KNOWN_PROJECTS (CLAUDE.md "Project
# slugs" rule): hermes / finance / wishlist, 1:1 with the router's profiles.
PROJECTS: dict[str, Project] = {
    "finance": {"repo": "sova-claw/hermes-finance", "base_branch": "main"},
    "wishlist": {"repo": "sova-claw/hermes-wishlist", "base_branch": "main"},
    "hermes": {"repo": "nkhimin/hermes-agent", "base_branch": "main"},
}


def get_project(name: str) -> Project | None:
    """Return the project config for a given slug, or None if unknown."""
    return PROJECTS.get(name)


_TOOL_DEFS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read a file from the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "ref": {"type": "string", "default": "main"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_directory",
        "description": "List directory contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "ref": {"type": "string", "default": "main"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_branch",
        "description": "Create a new git branch for the change.",
        "input_schema": {
            "type": "object",
            "properties": {"branch": {"type": "string"}},
            "required": ["branch"],
        },
    },
    {
        "name": "write_file",
        "description": "Write or update a file on the working branch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "branch": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["path", "content", "branch", "message"],
        },
    },
    {
        "name": "create_pr",
        "description": "Open a pull request with the changes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "head": {"type": "string"},
            },
            "required": ["title", "body", "head"],
        },
    },
    {
        "name": "merge_pr",
        "description": "Squash-merge the pull request.",
        "input_schema": {
            "type": "object",
            "properties": {"pr_number": {"type": "integer"}},
            "required": ["pr_number"],
        },
    },
]

# Tool subsets per phase — restricting available tools forces each model to stay
# in its lane without requiring heuristics about which model "should" call what.
_EXPLORE_TOOLS = [t for t in _TOOL_DEFS if t["name"] in {"read_file", "list_directory"}]
_CODE_TOOLS = [t for t in _TOOL_DEFS if t["name"] not in {"create_pr", "merge_pr"}]
_PR_TOOLS = [t for t in _TOOL_DEFS if t["name"] in {"create_pr", "merge_pr"}]

_SYSTEM = (
    "You are Doer, an autonomous developer agent. You make surgical code changes "
    "to GitHub repositories based on a natural-language task description.\n\n"
    "Workflow:\n"
    "1. Explore relevant files with read_file / list_directory.\n"
    "2. Identify the minimal change needed.\n"
    "3. Create a branch named doer/<short-slug> (lowercase, hyphens only).\n"
    "4. Write the changed files one by one.\n"
    "5. Create a PR with a title and a 1-2 sentence body.\n"
    "6. Merge the PR.\n\n"
    "Rules:\n"
    "- Change only what the task requires. No refactoring, no extra cleanup.\n"
    "- PR body: one sentence on what changed, one on why. Nothing else.\n"
    "- Never hardcode secrets or tokens.\n"
    "- If the task is ambiguous or impossible, stop and explain why."
)


class _GitHub:
    """Sync GitHub REST client — mirrors ``bots/doer/doer_api/agent/tools.py``
    one-for-one, just without ``async``/``await`` (see module docstring for
    why this loop runs sync-on-a-thread rather than on the event loop)."""

    def __init__(self, token: str):
        self._client = httpx.Client(
            base_url=_GITHUB_API_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )

    def read_file(self, repo: str, path: str, ref: str = "main") -> str:
        resp = self._client.get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return "\n".join(f["name"] for f in data)
        return base64.b64decode(data["content"]).decode()

    def list_directory(self, repo: str, path: str, ref: str = "main") -> str:
        resp = self._client.get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
        resp.raise_for_status()
        entries = resp.json()
        return "\n".join(f"{e['type']} {e['name']}" for e in entries)

    def _branch_sha(self, repo: str, branch: str) -> str:
        resp = self._client.get(f"/repos/{repo}/git/ref/heads/{branch}")
        resp.raise_for_status()
        return resp.json()["object"]["sha"]

    def create_branch(self, repo: str, branch: str, from_branch: str = "main") -> str:
        sha = self._branch_sha(repo, from_branch)
        resp = self._client.post(
            f"/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        resp.raise_for_status()
        return branch

    def write_file(
        self, repo: str, path: str, content: str, branch: str, message: str
    ) -> str:
        encoded = base64.b64encode(content.encode()).decode()
        payload: dict = {"message": message, "content": encoded, "branch": branch}
        check = self._client.get(
            f"/repos/{repo}/contents/{path}", params={"ref": branch}
        )
        if check.is_success and not isinstance(check.json(), list):
            payload["sha"] = check.json()["sha"]
        resp = self._client.put(f"/repos/{repo}/contents/{path}", json=payload)
        resp.raise_for_status()
        return resp.json()["commit"]["sha"]

    def create_pr(
        self, repo: str, title: str, body: str, head: str, base: str = "main"
    ) -> dict:
        resp = self._client.post(
            f"/repos/{repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base},
        )
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "url": data["html_url"]}

    def merge_pr(self, repo: str, pr_number: int) -> bool:
        resp = self._client.put(
            f"/repos/{repo}/pulls/{pr_number}/merge",
            json={"merge_method": "squash"},
        )
        if resp.status_code == 405:
            log.info(
                "pr_not_mergeable pr=%s reason=%s",
                pr_number,
                resp.json().get("message"),
            )
            return False
        resp.raise_for_status()
        return True


def _dispatch_tool(
    gh: _GitHub, tool_name: str, tool_input: dict, project: Project
) -> str:
    """Call the appropriate GitHub tool and return a string result."""
    repo = project["repo"]
    base = project["base_branch"]
    try:
        if tool_name == "read_file":
            return gh.read_file(repo, tool_input["path"], tool_input.get("ref", base))
        if tool_name == "list_directory":
            return gh.list_directory(
                repo, tool_input["path"], tool_input.get("ref", base)
            )
        if tool_name == "create_branch":
            branch = gh.create_branch(repo, tool_input["branch"], base)
            return f"Branch created: {branch}"
        if tool_name == "write_file":
            sha = gh.write_file(
                repo,
                tool_input["path"],
                tool_input["content"],
                tool_input["branch"],
                tool_input["message"],
            )
            return f"File written, commit: {sha[:7]}"
        if tool_name == "create_pr":
            pr = gh.create_pr(
                repo, tool_input["title"], tool_input["body"], tool_input["head"], base
            )
            return f"PR #{pr['number']}: {pr['url']}"
        if tool_name == "merge_pr":
            merged = gh.merge_pr(repo, tool_input["pr_number"])
            return (
                "Merged successfully."
                if merged
                else "Merge blocked (branch protection or CI required)."
            )
    except Exception as exc:
        log.warning("devops_tool_error tool=%s error=%s", tool_name, exc)
        return f"Error: {exc}"
    return f"Unknown tool: {tool_name}"


def _run_loop(
    client: anthropic.Anthropic,
    model: str,
    tools: list[dict],
    messages: list[dict],
    gh: "_GitHub",
    project: Project,
    max_iter: int,
) -> list[dict]:
    """Run one phase of the agent loop, returning the updated message history."""
    for _ in range(max_iter):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=_SYSTEM,
            tools=tools,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
            extra_body={"provider": {"require_parameters": True}},
        )
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        tool_results = []
        for block in tool_calls:
            result = _dispatch_tool(gh, block.name, block.input, project)  # type: ignore[arg-type]
            log.info("devops_tool_called tool=%s result=%s", block.name, result[:120])
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )
        messages.append({"role": "assistant", "content": response.content})  # type: ignore[arg-type]
        if response.stop_reason == "end_turn":
            break
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
    return messages


def _run_pr_phase(
    client: anthropic.Anthropic,
    model: str,
    messages: list[dict],
    gh: "_GitHub",
    project: Project,
) -> tuple[list[dict], str | None, bool]:
    """Run PR creation/merge phase. Returns (messages, pr_url, merged)."""
    pr_url: str | None = None
    merged = False
    for _ in range(5):
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=_SYSTEM,
            tools=_PR_TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
            extra_body={"provider": {"require_parameters": True}},
        )
        tool_calls = [b for b in response.content if b.type == "tool_use"]
        tool_results = []
        for block in tool_calls:
            result = _dispatch_tool(gh, block.name, block.input, project)  # type: ignore[arg-type]
            log.info("devops_tool_called tool=%s result=%s", block.name, result[:120])
            if block.name == "create_pr" and "http" in result:
                pr_url = result.split(": ", 1)[-1].strip()
            if block.name == "merge_pr" and "Merged" in result:
                merged = True
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )
        messages.append({"role": "assistant", "content": response.content})  # type: ignore[arg-type]
        if response.stop_reason == "end_turn":
            break
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
    return messages, pr_url, merged


@dataclass(frozen=True)
class DevopsLoop:
    """Runs the absorbed agentic loop against a profile's repo.

    Three-phase execution:
      1. Explore  — QUICK_MODEL reads files, understands the codebase (cheap)
      2. Code     — AGENT_MODEL writes the actual changes (Sonnet-class reasoning)
      3. PR ops   — QUICK_MODEL creates and merges the PR (cheap)

    ``dispatch`` is the only entry point callers need — it fires the loop on
    a background thread and returns immediately.
    """

    github_token: str
    llm_api_key: str
    agent_model: str
    quick_model: str
    telegram: TelegramClient

    def dispatch(self, profile: str, task: str) -> None:
        """Fire-and-forget: run ``task`` against ``profile``'s repo on a
        background thread. Swallows unknown-profile silently — the caller
        (``commands._handle_dev_task``) already validated the profile
        against the active selection before calling this."""
        project = get_project(profile)
        if project is None:
            return
        threading.Thread(
            target=self._run,
            args=(profile, project, task),
            daemon=True,
            name=f"devops-{profile}",
        ).start()

    def _run(self, profile: str, project: Project, task: str) -> None:
        log.info("devops_task_started profile=%s task=%s", profile, task[:120])
        gh = _GitHub(self.github_token)
        client = anthropic.Anthropic(base_url=_OPENROUTER_BASE_URL, api_key=self.llm_api_key)
        messages: list[dict] = [
            {"role": "user", "content": f"Project: {profile}\n\nTask: {task}"}
        ]

        try:
            # Phase 1: explore with quick model (read-only tools)
            log.info("devops_phase=explore model=%s", self.quick_model)
            messages = _run_loop(client, self.quick_model, _EXPLORE_TOOLS, messages, gh, project, max_iter=10)

            # Phase 2: code with agent model (branch + write tools)
            messages.append({"role": "user", "content": "Implement the changes: create a branch and write the files."})
            log.info("devops_phase=code model=%s", self.agent_model)
            messages = _run_loop(client, self.agent_model, _CODE_TOOLS, messages, gh, project, max_iter=20)

            # Phase 3: PR ops with quick model
            messages.append({"role": "user", "content": "Create a pull request for the changes, then merge it."})
            log.info("devops_phase=pr model=%s", self.quick_model)
            messages, pr_url, merged = _run_pr_phase(client, self.quick_model, messages, gh, project)

            log.info("devops_task_done profile=%s pr_url=%s merged=%s", profile, pr_url, merged)
            status = "merged" if merged else "PR open (merge blocked)"
            link = f"[{pr_url}]({pr_url})" if pr_url else "no PR created"
            self.telegram.send_message(
                _PROJECTS_CHAT, f"*Doer [{profile}]* — {status}\n{link}\n_{task[:120]}_"
            )
        except Exception as exc:
            log.error("devops_task_failed profile=%s error=%s", profile, exc)
            short = str(exc)[:200].replace("`", "'")
            self.telegram.send_message(
                _PROJECTS_CHAT, f"*Doer [{profile}]* — failed\n_{task[:80]}_\n`{short}`"
            )
