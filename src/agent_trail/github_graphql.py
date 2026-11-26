"""GitHub GraphQL API client for collecting repository metadata and agent config files."""

from __future__ import annotations

import os
from typing import Any

import httpx

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"

REPO_TREE_QUERY = """
query RepoAgentFiles($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    nameWithOwner
    stargazerCount
    forkCount
    primaryLanguage {
      name
    }
    createdAt
    pushedAt
    defaultBranchRef {
      name
      target {
        ... on Commit {
          history(first: 10) {
            nodes {
              oid
              committedDate
              message
            }
          }
        }
      }
    }
    object(expression: "HEAD:") {
      ... on Tree {
        entries {
          name
          type
        }
      }
    }
  }
  rateLimit {
    remaining
    resetAt
  }
}
"""


class GitHubGraphQLClient:
    """Thin wrapper around the GitHub GraphQL API."""

    def __init__(self, token: str | None = None, timeout: float = 30.0) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        if not self.token:
            raise ValueError("GITHUB_TOKEN must be provided or set in the environment.")
        self._client = httpx.Client(
            base_url=GITHUB_GRAPHQL_URL,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
            },
            timeout=timeout,
        )

    def query(self, query_str: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a GraphQL query and return the parsed JSON data payload."""
        response = self._client.post(
            "",
            json={"query": query_str, "variables": variables or {}},
        )
        response.raise_for_status()
        payload = response.json()
        if "errors" in payload:
            raise RuntimeError(f"GitHub GraphQL errors: {payload['errors']}")
        return payload["data"]

    def fetch_repository_snapshot(self, owner: str, name: str) -> dict[str, Any]:
        """Fetch basic metadata, root tree entries, and recent commits for a repository."""
        return self.query(REPO_TREE_QUERY, {"owner": owner, "name": name})

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> GitHubGraphQLClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
