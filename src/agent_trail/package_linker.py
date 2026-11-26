"""Link GitHub repositories to PyPI and npm packages."""

from __future__ import annotations

import re
from dataclasses import dataclass

GITHUB_URL_RE = re.compile(
    r"(?:https?://|git\+https?://|git://|ssh://git@)?github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s#?]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PackageLink:
    """Represents a linkage between a package registry entry and a GitHub repository."""

    ecosystem: str  # "pypi" or "npm"
    package_name: str
    repo_full_name: str


def normalize_github_repo(url: str | None) -> str | None:
    """Extract canonical 'owner/repo' from a GitHub URL, or return None if not a match."""
    if not url:
        return None
    match = GITHUB_URL_RE.search(url.strip())
    if not match:
        return None
    owner = match.group("owner").lower()
    repo = match.group("repo").removesuffix(".git").lower()
    return f"{owner}/{repo}"


def extract_pypi_repo(metadata: dict) -> PackageLink | None:
    """Extract a GitHub repository link from a PyPI JSON API metadata payload."""
    info = metadata.get("info") or {}
    package_name = info.get("name", "")
    project_urls = info.get("project_urls") or {}
    candidates = [
        info.get("home_page"),
        project_urls.get("Source"),
        project_urls.get("Repository"),
        project_urls.get("Homepage"),
        project_urls.get("Code"),
    ]
    for candidate in candidates:
        repo = normalize_github_repo(candidate)
        if repo and package_name:
            return PackageLink(
                ecosystem="pypi",
                package_name=package_name,
                repo_full_name=repo,
            )
    return None


def extract_npm_repo(metadata: dict) -> PackageLink | None:
    """Extract a GitHub repository link from an npm registry metadata payload."""
    package_name = metadata.get("name", "")
    repository = metadata.get("repository")
    repo_url = repository.get("url") if isinstance(repository, dict) else repository
    candidates = [repo_url, metadata.get("homepage")]
    for candidate in candidates:
        repo = normalize_github_repo(candidate)
        if repo and package_name:
            return PackageLink(
                ecosystem="npm",
                package_name=package_name,
                repo_full_name=repo,
            )
    return None
