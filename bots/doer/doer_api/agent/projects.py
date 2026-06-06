"""Project registry — maps command slugs to GitHub repos."""

from typing import TypedDict


class Project(TypedDict):
    """GitHub project target."""

    repo: str
    base_branch: str


PROJECTS: dict[str, Project] = {
    "finance": {"repo": "sova-claw/hermes-finance", "base_branch": "main"},
    "wishlist": {"repo": "sova-claw/hermes-wishlist", "base_branch": "main"},
    "hermes": {"repo": "nkhimin/hermes-agent", "base_branch": "main"},
}


def get_project(name: str) -> Project | None:
    """Return the project config for a given slug, or None if unknown."""
    return PROJECTS.get(name)
