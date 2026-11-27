# AgentTrail

**AI Coding Agent Adoption in Open Source ($0-Cost Local Pipeline)**

AgentTrail measures the adoption and impact of AI coding agents (Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Devin) across open source repositories and GitHub event streams—using **100% free, local, open-source tools** and **zero paid cloud services**.

## $0-Cost Architecture

| Component | Free Source / Tool | Replaces Paid Option |
| :--- | :--- | :--- |
| **GitHub metadata & PRs** | GitHub GraphQL / REST API (`GITHUB_TOKEN` / `gh auth token`) | — |
| **GH Archive events** | Direct hourly `.json.gz` downloads (`data.gharchive.org`) | BigQuery `githubarchive` |
| **Package & dependency links** | `api.deps.dev/v3`, `pypi.org/pypi/.../json`, `registry.npmjs.org` | BigQuery `deps_dev_v1` |
| **Storage & SQL joins** | Local Parquet + DuckDB | AWS S3 / ClickHouse / Dataflow |
| **Statistical analysis** | Local R (`did`, `fixest`, `survival`, `modelsummary`) | — |
| **Paper & tables** | Local LaTeX (`tectonic`) | — |

## Pipeline Overview

1. **Signal Detection (`src/agent_trail/signals.py`)**: Identifies repository-level agent configuration files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.cursor/rules/*`, `.github/copilot-instructions.md`) and commit/PR co-author trailers.
2. **GitHub GraphQL Collector (`src/agent_trail/github_graphql.py`)**: Collects repository metadata, file trees, and adoption timestamps via the GitHub GraphQL API.
3. **GH Archive Event Stream (`src/agent_trail/gh_archive.py`)**: Streams and filters hourly GH Archive `.json.gz` events (`PushEvent`, `PullRequestEvent`) for agent-attributed activity.
4. **Package Linkage (`src/agent_trail/package_linker.py`)**: Links GitHub repositories to PyPI and npm packages via repository URL normalization.
5. **Statistical Analysis (`r/event_study.R`, `slurm/run_analysis.sh`)**: Runs descriptive statistics and event studies in R (locally or on free university Slurm clusters).

## Setup

```bash
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev]"
pytest
```
