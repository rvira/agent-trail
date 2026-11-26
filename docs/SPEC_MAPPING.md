# AgentTrail: Project Guide & Spec Mapping

This document explains how **AgentTrail** works, how it maps to the project specification ([`OSS_Research_Project_Spec.md`](../../Resumes/InternshipResumes/project%20ideas/OSS_Research_Project_Spec.md)), and what is **implemented today (`v0.1.0` scaffold)** versus **planned for the Week 1–6 milestones**.

---

## 1. What AgentTrail Does (Plain-English Overview)

AgentTrail is an empirical research pipeline that measures **what happens to open source projects when AI coding agents (Claude Code, Cursor, GitHub Copilot, Codex, Devin) are adopted**.

It works in five stages:
1. **Detect adoption signals** — Spot when a repo starts using an AI agent via config files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, etc.), commit trailers (`Co-Authored-By: Claude`), or bot PR authors (`copilot-swe-agent[bot]`).
2. **Collect repo & event history** — Pull repository metadata and PR/review timelines from the GitHub API, bulk event history from GH Archive (via BigQuery), and exact first-commit dates from shallow git clones on a Slurm cluster.
3. **Link packages & resolve identities** — Match GitHub repos to PyPI and npm packages (via `deps.dev` and registry metadata) and merge/hash contributor identities while flagging bots.
4. **Build a `repo × month` panel** — Combine outcomes (merged PRs, review latency, issue close time, newcomer retention, bus factor) with adoption timing.
5. **Run econometrics & generate paper outputs** — Estimate pre/post adoption changes in R (Callaway & Sant'Anna `did`, Sun & Abraham `fixest::sunab`, survival models) and export LaTeX tables and figures.

---

## 2. Spec-to-Code Component Map

### A. Pipeline Architecture (Spec §5)

| Spec Stage | Spec Responsibility | Current Location in `agent-trail` | Status |
| :--- | :--- | :--- | :--- |
| **`collect/`** | GitHub GraphQL + REST collectors, BigQuery extracts, git clone jobs | [`src/agent_trail/github_graphql.py`](../src/agent_trail/github_graphql.py), [`src/agent_trail/gh_archive.py`](../src/agent_trail/gh_archive.py) | **Partial** — Basic GraphQL snapshot query & local `.json.gz` GH Archive parser exist. Missing `tenacity` retries, rate-limit token bucket, checkpointing, REST file checks, BigQuery extracts, and Slurm git-clone array jobs. |
| **`stage/`** | Schema validation (`pandera`), deduplication, Parquet outputs | *Not yet created* | **Missing** — Needs `pandera` schemas and staged Parquet tables (`repos`, `prs`, `reviews`, `issues`, `commits`, `contributors`). |
| **`link/`** | Identity resolution, email hashing, bot detection, `repo ↔ package ↔ dependents` | [`src/agent_trail/package_linker.py`](../src/agent_trail/package_linker.py) | **Partial** — URL normalization and PyPI/npm metadata extraction exist. Missing `deps.dev` BigQuery linkage, DuckDB joins, contributor identity merging, and email hashing. |
| **`panel/`** | DuckDB `repo × month` panel with outcomes and treatment flags | *Not yet created* | **Missing** — Needs SQL/DuckDB scripts to aggregate events into `repo × month` rows (Jan 2022–present). |
| **`analysis/`** | R descriptives, `did`, `fixest::sunab`, `survival`, `modelsummary` tables & figures | [`r/event_study.R`](../r/event_study.R), [`slurm/run_analysis.sh`](../slurm/run_analysis.sh) | **Placeholder** — Currently has a basic `aggregate()` + `lm()` stub and a Slurm batch script. Needs `did`, `fixest`, `survival`, `modelsummary`, and Week 1 Jupyter notebook. |
| **`paper/`** | LaTeX working paper, generated `figures/` and `tables/` | *Not yet created* | **Missing** — Week 1 pilot requires at least a generated LaTeX Table 1; full paper is Week 6. |

---

### B. Adoption Signals / Treatment Definition (Spec §3)

| Spec Signal | Spec Requirement | Current Implementation | Status |
| :--- | :--- | :--- | :--- |
| **Config files** | `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.cursor/rules/`, `.github/copilot-instructions.md`, `GEMINI.md` | [`AGENT_CONFIG_PATHS` in `signals.py`](../src/agent_trail/signals.py) | **Mostly followed** — Includes all listed paths **except `GEMINI.md`** (also includes `.claude/settings.json`, `CODEX.md`, `.windsurfrules`, `.clinerules`). |
| **Co-author trailers** | `Co-Authored-By: Claude`, `Copilot`, etc. | [`COMMIT_TRAILER_PATTERNS` in `signals.py`](../src/agent_trail/signals.py) | **Followed** — Covers Claude, Cursor, Copilot, and Codex trailers. |
| **Bot PR authors** | `copilot-swe-agent[bot]`, `devin-ai-integration[bot]`, `claude[bot]`, etc. | *Not yet implemented* | **Missing** — Needs a bot-author detector and separate per-signal flags. |
| **Separate signal flags** | Keep each signal as its own flag for robustness checks | `AgentSignal(agent, source, marker)` | **Followed** — Signals are tagged by `agent` and `source`. |

---

### C. Engineering & Deliverables Checklist (Spec §5, §6.5, §7, §11)

| Spec Item | Current Status | Where / Next Action |
| :--- | :--- | :--- |
| **Unit tests (`pytest`)** | **Followed (4 tests)** | [`tests/test_signals.py`](../tests/test_signals.py) — covers config signals, commit trailers, GH Archive extraction, and PyPI/npm linkage. |
| **GitHub Actions CI** | **Missing** | Add `.github/workflows/ci.yml` to run `pytest` on push/PR. |
| **Reproducibility (`uv` / `renv` / `Makefile`)** | **Partial** | [`pyproject.toml`](../pyproject.toml) exists; add `uv.lock`, `renv.lock`, and a `Makefile` for `make all`. |
| **Signal validation (200-repo sample)** | **Missing** | Needed before modeling (Spec §6.5). |
| **Deliverables (`UPDATES.md`, Data Dictionary)** | **Missing** | Add `UPDATES.md` (weekly log) and `docs/DATA_DICTIONARY.md` (Spec §7). |
| **Jupyter + LaTeX pilot proof** | **Missing** | Spec §11 notes Jupyter and LaTeX on the resume are backed by the Week 1 pilot (exploration notebook + LaTeX Table 1). |

---

## 3. Recommended Next Steps (Week 1 Pilot Path)

1. **Close signal gaps:** Add `GEMINI.md` and bot PR author detection (`copilot-swe-agent[bot]`, `devin-ai-integration[bot]`, `claude[bot]`) to `signals.py` + tests.
2. **Add BigQuery + `deps.dev` sampler:** Query `bigquery-public-data.deps_dev_v1` for 500 pilot repos (250 PyPI + 250 npm, ≥50 stars, active ≥12 months before Jan 2024) and extract their `githubarchive` events.
3. **Harden GraphQL collector:** Add `tenacity` exponential backoff, rate-limit tracking, and per-repo JSON/Parquet checkpointing.
4. **Build Week 1 Pilot outputs:** Stage Parquet tables, explore in a Jupyter notebook, and generate Figure 1 (adoption curve) and a LaTeX Table 1.
