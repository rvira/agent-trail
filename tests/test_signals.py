"""Unit tests for AgentTrail signal detection, GH Archive parsing, and package linking."""

from agent_trail.gh_archive import extract_agent_events
from agent_trail.package_linker import (
    extract_npm_repo,
    extract_pypi_repo,
    normalize_github_repo,
)
from agent_trail.signals import detect_bot_author, detect_commit_signals, detect_config_signals


def test_detect_config_signals() -> None:
    paths = [
        "README.md",
        "CLAUDE.md",
        "GEMINI.md",
        ".cursor/rules/python.mdc",
        ".github/copilot-instructions.md",
        "src/main.py",
    ]
    signals = detect_config_signals(paths)
    agents = {(s.agent, s.marker) for s in signals}
    assert ("claude_code", "CLAUDE.md") in agents
    assert ("gemini_cli", "GEMINI.md") in agents
    assert ("cursor", ".cursor/rules/python.mdc") in agents
    assert ("copilot", ".github/copilot-instructions.md") in agents
    assert len(agents) == 4


def test_detect_bot_author() -> None:
    sig = detect_bot_author("copilot-swe-agent[bot]")
    assert sig is not None
    assert sig.agent == "copilot"
    assert sig.source == "bot_author"
    assert detect_bot_author("octocat") is None


def test_detect_commit_signals() -> None:
    msg = "feat: add parser\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
    signals = detect_commit_signals(msg)
    assert len(signals) == 1
    assert signals[0].agent == "claude_code"
    assert signals[0].source == "commit_trailer"


def test_extract_agent_events() -> None:
    raw_events = iter(
        [
            {
                "id": "101",
                "type": "PushEvent",
                "repo": {"name": "rvira/agent-trail"},
                "created_at": "2026-11-01T12:00:00Z",
                "payload": {
                    "commits": [
                        {"message": "fix: edge case\n\nCo-Authored-By: Cursor <cursoragent@cursor.com>"}
                    ]
                },
            },
            {
                "id": "102",
                "type": "WatchEvent",
                "repo": {"name": "rvira/agent-trail"},
                "created_at": "2026-11-01T12:01:00Z",
                "payload": {},
            },
        ]
    )
    records = list(extract_agent_events(raw_events))
    assert len(records) == 1
    assert records[0].event_id == "101"
    assert records[0].repo_name == "rvira/agent-trail"
    assert records[0].signals[0].agent == "cursor"


def test_normalize_github_repo_and_package_linkers() -> None:
    assert normalize_github_repo("git+https://github.com/Rvira/Agent-Trail.git") == "rvira/agent-trail"
    assert normalize_github_repo("https://gitlab.com/user/repo") is None

    pypi_link = extract_pypi_repo(
        {
            "info": {
                "name": "agent-trail",
                "project_urls": {"Source": "https://github.com/rvira/agent-trail"},
            }
        }
    )
    assert pypi_link is not None
    assert pypi_link.ecosystem == "pypi"
    assert pypi_link.repo_full_name == "rvira/agent-trail"

    npm_link = extract_npm_repo(
        {
            "name": "agent-trail-cli",
            "repository": {"type": "git", "url": "git+https://github.com/rvira/agent-trail.git"},
        }
    )
    assert npm_link is not None
    assert npm_link.ecosystem == "npm"
    assert npm_link.repo_full_name == "rvira/agent-trail"
