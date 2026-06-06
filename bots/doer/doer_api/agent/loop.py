"""OpenRouter-backed agentic loop for autonomous code changes."""

from datetime import UTC, datetime

import anthropic
import structlog

from doer_api.agent import tools as gh
from doer_api.agent.projects import Project, get_project
from doer_api.core.config import settings
from doer_api.telegram import send_to_projects

log = structlog.get_logger(__name__)

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
            "properties": {
                "branch": {"type": "string"},
            },
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
            "properties": {
                "pr_number": {"type": "integer"},
            },
            "required": ["pr_number"],
        },
    },
]

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


async def _dispatch_tool(
    tool_name: str, tool_input: dict, project: Project
) -> str:
    """Call the appropriate GitHub tool and return a string result."""
    repo = project["repo"]
    base = project["base_branch"]
    try:
        if tool_name == "read_file":
            return await gh.read_file(
                repo, tool_input["path"], tool_input.get("ref", base)
            )
        if tool_name == "list_directory":
            return await gh.list_directory(
                repo, tool_input["path"], tool_input.get("ref", base)
            )
        if tool_name == "create_branch":
            branch = await gh.create_branch(repo, tool_input["branch"], base)
            return f"Branch created: {branch}"
        if tool_name == "write_file":
            sha = await gh.write_file(
                repo,
                tool_input["path"],
                tool_input["content"],
                tool_input["branch"],
                tool_input["message"],
            )
            return f"File written, commit: {sha[:7]}"
        if tool_name == "create_pr":
            pr = await gh.create_pr(
                repo,
                tool_input["title"],
                tool_input["body"],
                tool_input["head"],
                base,
            )
            return f"PR #{pr['number']}: {pr['url']}"
        if tool_name == "merge_pr":
            merged = await gh.merge_pr(repo, tool_input["pr_number"])
            return (
                "Merged successfully."
                if merged
                else "Merge blocked (branch protection or CI required)."
            )
    except Exception as exc:
        log.warning("tool_error", tool=tool_name, error=str(exc))
        return f"Error: {exc}"
    return f"Unknown tool: {tool_name}"


async def run(
    task_id: str, project_name: str, task: str, task_store: dict
) -> None:
    """Run the agentic loop for a task. Updates task_store in place."""
    project = get_project(project_name)
    if project is None:
        task_store[task_id] = {
            "status": "failed",
            "error": f"Unknown project: {project_name}",
        }
        return

    task_store[task_id] = {
        "status": "running",
        "started_at": datetime.now(UTC).isoformat(),
    }
    log.info("doer_task_started", task_id=task_id, project=project_name)

    client = anthropic.AsyncAnthropic(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )

    messages: list[dict] = [
        {"role": "user", "content": f"Project: {project_name}\n\nTask: {task}"}
    ]
    pr_url: str | None = None
    merged = False

    try:
        for _ in range(30):  # safety cap
            response = await client.messages.create(
                model=settings.doer_model,
                max_tokens=4096,
                system=_SYSTEM,
                tools=_TOOL_DEFS,  # type: ignore[arg-type]
                messages=messages,  # type: ignore[arg-type]
            )

            tool_calls = [b for b in response.content if b.type == "tool_use"]

            tool_results = []
            for block in tool_calls:
                result = await _dispatch_tool(
                    block.name, block.input, project  # type: ignore[arg-type]
                )
                log.info("tool_called", tool=block.name, result=result[:120])

                if block.name == "create_pr" and "http" in result:
                    pr_url = result.split(": ", 1)[-1].strip()
                if block.name == "merge_pr" and "Merged" in result:
                    merged = True

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages.append(
                {"role": "assistant", "content": response.content}  # type: ignore[arg-type]
            )

            if response.stop_reason == "end_turn":
                break

            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        task_store[task_id] = {
            "status": "done",
            "pr_url": pr_url,
            "merged": merged,
        }
        log.info("doer_task_done", task_id=task_id, pr_url=pr_url, merged=merged)

        status = "merged" if merged else "PR open (merge blocked)"
        link = f'<a href="{pr_url}">{pr_url}</a>' if pr_url else "no PR created"
        await send_to_projects(
            f"<b>Doer [{project_name}]</b> — {status}\n{link}\n<i>{task[:120]}</i>"
        )

    except Exception as exc:
        log.error("doer_task_failed", task_id=task_id, error=str(exc))
        task_store[task_id] = {"status": "failed", "error": str(exc)}
        short = str(exc)[:200]
        await send_to_projects(
            f"<b>Doer [{project_name}]</b> — failed\n"
            f"<i>{task[:80]}</i>\n<code>{short}</code>"
        )
