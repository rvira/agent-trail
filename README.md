# AgentTrail

**AI Coding Agent Adoption in Open Source**

AgentTrail measures the adoption and impact of AI coding agents (Claude Code, Cursor, GitHub Copilot, OpenAI Codex, etc.) across open source repositories and GitHub event streams.

## Pipeline Overview

1. **Signal Detection (`src/agent_trail/signals.py`)**: Identifies repository-level agent configuration files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.cursor/rules/*`, `.github/copilot-instructions.md`) and commit/PR co-author trailers.
2. **GitHub GraphQL Collector (`src/agent_trail/github_graphql.py`)**: Collects repository metadata, file trees, and adoption timestamps via the GitHub GraphQL API.
3. **GH Archive Event Stream (`src/agent_trail/gh_archive.py`)**: Streams and filters hourly GH Archive JSON events (`PushEvent`, `PullRequestEvent`) for agent-attributed activity.
4. **Package Linkage (`src/agent_trail/package_linker.py`)**: Links GitHub repositories to PyPI and npm packages via repository URL normalization.
5. **Statistical Analysis (`r/event_study.R`, `slurm/run_analysis.sh`)**: Runs descriptive statistics and event studies in R (designed for Slurm batch execution) to evaluate changes in development velocity and release cadence around adoption.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
