"""Detection rules for AI coding agent adoption signals in repositories and events."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Repository file paths indicating AI coding agent configuration
AGENT_CONFIG_PATHS: dict[str, str] = {
    "CLAUDE.md": "claude_code",
    ".claude/settings.json": "claude_code",
    ".cursorrules": "cursor",
    ".cursor/rules": "cursor",
    "AGENTS.md": "codex",
    "CODEX.md": "codex",
    ".github/copilot-instructions.md": "copilot",
    ".windsurfrules": "windsurf",
    ".clinerules": "cline",
}

# Patterns in commit messages or PR bodies indicating agent-authored/co-authored work
COMMIT_TRAILER_PATTERNS: dict[str, re.Pattern[str]] = {
    "claude_code": re.compile(
        r"Co-Authored-By:\s*Claude\b|noreply@anthropic\.com", re.IGNORECASE
    ),
    "cursor": re.compile(
        r"Co-Authored-By:\s*Cursor\b|cursoragent@", re.IGNORECASE
    ),
    "copilot": re.compile(
        r"Co-Authored-By:\s*GitHub Copilot\b|copilot@github\.com", re.IGNORECASE
    ),
    "codex": re.compile(
        r"Co-Authored-By:\s*(?:OpenAI\s+)?Codex\b", re.IGNORECASE
    ),
}


@dataclass(frozen=True)
class AgentSignal:
    """Represents a detected AI coding agent signal."""

    agent: str
    source: str  # "config_file" or "commit_trailer"
    marker: str


def detect_config_signals(paths: list[str]) -> list[AgentSignal]:
    """Identify AI coding agent signals from a list of repository file paths."""
    signals: list[AgentSignal] = []
    for path in paths:
        normalized = path.removeprefix("./")
        for prefix, agent in AGENT_CONFIG_PATHS.items():
            if normalized == prefix or normalized.startswith(f"{prefix}/"):
                signals.append(
                    AgentSignal(agent=agent, source="config_file", marker=normalized)
                )
    return signals


def detect_commit_signals(message: str) -> list[AgentSignal]:
    """Identify AI coding agent co-author trailers in a commit or PR message."""
    signals: list[AgentSignal] = []
    for agent, pattern in COMMIT_TRAILER_PATTERNS.items():
        match = pattern.search(message)
        if match:
            signals.append(
                AgentSignal(agent=agent, source="commit_trailer", marker=match.group(0))
            )
    return signals
