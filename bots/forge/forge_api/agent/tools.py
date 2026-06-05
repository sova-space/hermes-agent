"""GitHub REST API tool implementations for the Forge agent."""

import base64

import httpx
import structlog

from forge_api.core.config import settings

log = structlog.get_logger(__name__)

_HEADERS = {
    "Authorization": f"Bearer {settings.github_token}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.github_api_url,
        headers=_HEADERS,
        timeout=30,
    )


async def read_file(repo: str, path: str, ref: str = "main") -> str:
    """Return the decoded text content of a file."""
    async with _client() as gh:
        resp = await gh.get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return "\n".join(f["name"] for f in data)
        return base64.b64decode(data["content"]).decode()


async def list_directory(repo: str, path: str, ref: str = "main") -> str:
    """Return a newline-separated list of entries in a directory."""
    async with _client() as gh:
        resp = await gh.get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
        resp.raise_for_status()
        entries = resp.json()
        return "\n".join(f"{e['type']} {e['name']}" for e in entries)


async def get_default_branch_sha(repo: str, branch: str) -> str:
    """Return the latest commit SHA on a branch."""
    async with _client() as gh:
        resp = await gh.get(f"/repos/{repo}/git/ref/heads/{branch}")
        resp.raise_for_status()
        return resp.json()["object"]["sha"]


async def create_branch(repo: str, branch: str, from_branch: str = "main") -> str:
    """Create a new branch from the tip of from_branch. Returns the new branch name."""
    sha = await get_default_branch_sha(repo, from_branch)
    async with _client() as gh:
        resp = await gh.post(
            f"/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )
        resp.raise_for_status()
    return branch


async def write_file(
    repo: str,
    path: str,
    content: str,
    branch: str,
    message: str,
) -> str:
    """Create or update a file on a branch. Returns the commit SHA."""
    encoded = base64.b64encode(content.encode()).decode()
    payload: dict = {"message": message, "content": encoded, "branch": branch}

    # If file exists, include its SHA to update rather than create
    async with _client() as gh:
        check = await gh.get(f"/repos/{repo}/contents/{path}", params={"ref": branch})
        if check.is_success and not isinstance(check.json(), list):
            payload["sha"] = check.json()["sha"]

        resp = await gh.put(f"/repos/{repo}/contents/{path}", json=payload)
        resp.raise_for_status()
        return resp.json()["commit"]["sha"]


async def create_pr(
    repo: str,
    title: str,
    body: str,
    head: str,
    base: str = "main",
) -> dict:
    """Open a pull request. Returns {number, url}."""
    async with _client() as gh:
        resp = await gh.post(
            f"/repos/{repo}/pulls",
            json={"title": title, "body": body, "head": head, "base": base},
        )
        resp.raise_for_status()
        data = resp.json()
        return {"number": data["number"], "url": data["html_url"]}


async def merge_pr(repo: str, pr_number: int) -> bool:
    """Squash-merge a pull request. Returns True on success."""
    async with _client() as gh:
        resp = await gh.put(
            f"/repos/{repo}/pulls/{pr_number}/merge",
            json={"merge_method": "squash"},
        )
        if resp.status_code == 405:
            log.info(
                "pr_not_mergeable",
                pr=pr_number,
                reason=resp.json().get("message"),
            )
            return False
        resp.raise_for_status()
        return True
