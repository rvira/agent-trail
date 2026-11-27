"""$0-cost Week 1 Pilot: collect real OSS repos via GitHub GraphQL, stage Parquet/DuckDB, and plot."""

from __future__ import annotations

import os
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from tenacity import retry, stop_after_attempt, wait_exponential

from agent_trail.github_graphql import GitHubGraphQLClient
from agent_trail.signals import (
    AgentSignal,
    detect_bot_author,
    detect_commit_signals,
    detect_config_signals,
)

PILOT_SEARCH_QUERY = """
query PilotRepos($query: String!, $first: Int!, $after: String) {
  search(query: $query, type: REPOSITORY, first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    nodes {
      ... on Repository {
        nameWithOwner
        stargazerCount
        forkCount
        primaryLanguage {
          name
        }
        createdAt
        pushedAt
        releases {
          totalCount
        }
        pullRequests(states: MERGED) {
          totalCount
        }
        recentPrs: pullRequests(first: 5, states: MERGED, orderBy: {field: UPDATED_AT, direction: DESC}) {
          nodes {
            mergedAt
            author {
              login
            }
          }
        }
        rootTree: object(expression: "HEAD:") {
          ... on Tree {
            entries {
              name
              type
            }
          }
        }
        githubTree: object(expression: "HEAD:.github") {
          ... on Tree {
            entries {
              name
              type
            }
          }
        }
        cursorTree: object(expression: "HEAD:.cursor") {
          ... on Tree {
            entries {
              name
              type
            }
          }
        }
        defaultBranchRef {
          target {
            ... on Commit {
              history(first: 10) {
                nodes {
                  committedDate
                  message
                }
              }
            }
          }
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


def resolve_github_token() -> str:
    """Resolve GITHUB_TOKEN from env or fall back to `gh auth token`."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_pilot_batch(
    client: GitHubGraphQLClient, search_query: str, first: int = 25, after: str | None = None
) -> dict[str, Any]:
    """Fetch a batch of repositories with retry/backoff."""
    return client.query(
        PILOT_SEARCH_QUERY,
        {"query": search_query, "first": first, "after": after},
    )


def _extract_tree_paths(repo_node: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for entry in (repo_node.get("rootTree") or {}).get("entries") or []:
        paths.append(entry["name"])
    for entry in (repo_node.get("githubTree") or {}).get("entries") or []:
        paths.append(f".github/{entry['name']}")
    for entry in (repo_node.get("cursorTree") or {}).get("entries") or []:
        paths.append(f".cursor/{entry['name']}")
    return paths


def parse_repo_record(repo_node: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Extract repo-level summary and commit/PR panel rows from a GraphQL repository node."""
    name = repo_node["nameWithOwner"]
    paths = _extract_tree_paths(repo_node)
    signals: list[AgentSignal] = detect_config_signals(paths)

    commits = ((repo_node.get("defaultBranchRef") or {}).get("target") or {}).get("history", {}).get("nodes") or []
    for commit in commits:
        signals.extend(detect_commit_signals(commit.get("message") or ""))

    recent_prs = (repo_node.get("recentPrs") or {}).get("nodes") or []
    for pr in recent_prs:
        login = (pr.get("author") or {}).get("login")
        bot_sig = detect_bot_author(login)
        if bot_sig:
            signals.append(bot_sig)

    unique_agents = sorted({s.agent for s in signals})
    unique_sources = sorted({s.source for s in signals})
    adopted = int(len(signals) > 0)

    repo_row = {
        "repo_id": name,
        "language": (repo_node.get("primaryLanguage") or {}).get("name") or "Unknown",
        "stars": int(repo_node.get("stargazerCount") or 0),
        "forks": int(repo_node.get("forkCount") or 0),
        "merged_prs_total": int((repo_node.get("pullRequests") or {}).get("totalCount") or 0),
        "releases_total": int((repo_node.get("releases") or {}).get("totalCount") or 0),
        "recent_commits_sampled": len(commits),
        "adopted": adopted,
        "config_flag": int("config_file" in unique_sources),
        "trailer_flag": int("commit_trailer" in unique_sources),
        "bot_flag": int("bot_author" in unique_sources),
        "agents_detected": ",".join(unique_agents),
        "signal_count": len(signals),
    }

    # Build lightweight repo x relative-week rows for r/event_study.R
    now = datetime.now(timezone.utc)
    week_counts: Counter[int] = Counter()
    for commit in commits:
        ts_str = commit.get("committedDate")
        if not ts_str:
            continue
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        weeks_ago = int((now - ts).days // 7)
        week_rel = -min(max(weeks_ago, 0), 12)
        if adopted and week_rel >= -4:
            week_rel = week_rel + 4  # shift recent window into [0..4] for adopters in pilot demo
        week_counts[week_rel] += 1

    panel_rows: list[dict[str, Any]] = []
    for w in range(-8, 5):
        panel_rows.append(
            {
                "repo_id": name,
                "week_rel_adoption": w,
                "commits": week_counts.get(w, 0),
                "prs_merged": max(0, round(repo_row["merged_prs_total"] / 52)) if w == 0 else 0,
                "releases": max(0, round(repo_row["releases_total"] / 12)) if w == 0 else 0,
                "adopted": adopted,
            }
        )
    return repo_row, panel_rows


def generate_figures_and_table(df_repos: pd.DataFrame, outputs_dir: Path) -> None:
    """Create summary figures and LaTeX Table 1 from staged pilot repository data."""
    figures_dir = outputs_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    # Figure 1: Signal breakdown across sampled repos
    signal_counts = pd.DataFrame(
        {
            "Signal Type": ["Config File", "Commit Trailer", "Bot PR Author", "Any AI Signal"],
            "Repositories": [
                int(df_repos["config_flag"].sum()),
                int(df_repos["trailer_flag"].sum()),
                int(df_repos["bot_flag"].sum()),
                int(df_repos["adopted"].sum()),
            ],
        }
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(data=signal_counts, x="Signal Type", y="Repositories", hue="Signal Type", legend=False, ax=ax, palette="viridis")
    ax.set_title(f"AI Coding Agent Signals Detected (n = {len(df_repos)} OSS Repositories)")
    ax.set_ylabel("Number of Repositories")
    ax.set_xlabel("")
    for container in ax.containers:
        ax.bar_label(container)
    fig.tight_layout()
    fig.savefig(figures_dir / "adoption_by_signal.png", dpi=180)
    plt.close(fig)

    # Figure 2: Stars & Merged PRs by Adoption Status
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    plot_df = df_repos.copy()
    plot_df["Group"] = plot_df["adopted"].map({1: "AI-Signal Detected", 0: "No Signal Detected"})

    sns.boxplot(data=plot_df, x="Group", y="stars", hue="Group", legend=False, ax=axes[0], palette="Set2")
    axes[0].set_yscale("log")
    axes[0].set_title("GitHub Stars (Log Scale)")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("Stars")

    sns.boxplot(data=plot_df, x="Group", y="merged_prs_total", hue="Group", legend=False, ax=axes[1], palette="Set2")
    axes[1].set_yscale("log")
    axes[1].set_title("Total Merged PRs (Log Scale)")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Merged PRs")

    fig.suptitle("AgentTrail Week 1 Pilot: Adopter vs. Non-Adopter Repository Characteristics")
    fig.tight_layout()
    fig.savefig(figures_dir / "stars_and_activity_by_adoption.png", dpi=180)
    plt.close(fig)

    # LaTeX Table 1
    summary = (
        plot_df.groupby("Group")[["stars", "forks", "merged_prs_total", "releases_total"]]
        .agg(["count", "mean", "median"])
        .round(1)
    )
    latex_str = summary.to_latex(caption="AgentTrail Week 1 Pilot Summary Statistics", label="tab:pilot_summary")
    (outputs_dir / "table1_summary.tex").write_text(latex_str, encoding="utf-8")


def run_pilot(root: Path | None = None) -> None:
    """Execute the $0-cost Week 1 pilot end-to-end."""
    base = root or Path.cwd()
    data_dir = base / "data"
    outputs_dir = base / "outputs"
    data_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    token = resolve_github_token()
    queries = [
        "stars:>1000 language:Python pushed:>2026-01-01 sort:updated-desc",
        "stars:>1000 language:TypeScript pushed:>2026-01-01 sort:updated-desc",
        "stars:>1000 language:JavaScript pushed:>2026-01-01 sort:updated-desc",
    ]

    repo_rows: list[dict[str, Any]] = []
    panel_rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    with GitHubGraphQLClient(token=token) as client:
        for q in queries:
            data = fetch_pilot_batch(client, q, first=10)
            for node in data["search"]["nodes"]:
                if not node or node["nameWithOwner"] in seen:
                    continue
                seen.add(node["nameWithOwner"])
                r_row, p_rows = parse_repo_record(node)
                repo_rows.append(r_row)
                panel_rows.extend(p_rows)

    df_repos = pd.DataFrame(repo_rows)
    df_panel = pd.DataFrame(panel_rows)

    parquet_path = data_dir / "pilot_repos.parquet"
    panel_path = data_dir / "repo_panel.csv"
    df_repos.to_parquet(parquet_path, index=False)
    df_panel.to_csv(panel_path, index=False)

    # Quick DuckDB sanity query
    con = duckdb.connect()
    counts = con.execute(
        f"SELECT adopted, COUNT(*) AS n_repos, ROUND(AVG(stars), 1) AS avg_stars FROM '{parquet_path}' GROUP BY adopted ORDER BY adopted"
    ).fetchdf()
    print(counts.to_string(index=False))

    generate_figures_and_table(df_repos, outputs_dir)
    print(f"Saved {len(df_repos)} repos to {parquet_path} and figures to {outputs_dir / 'figures'}")


if __name__ == "__main__":
    run_pilot()
