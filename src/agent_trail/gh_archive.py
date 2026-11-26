"""GH Archive event stream parser for detecting agent-attributed GitHub activity."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_trail.signals import AgentSignal, detect_commit_signals


@dataclass(frozen=True)
class AgentEventRecord:
    """Extracted event record where an AI coding agent signal was detected."""

    event_id: str
    event_type: str
    repo_name: str
    created_at: str
    signals: tuple[AgentSignal, ...]


def iter_gh_archive_events(path: Path) -> Iterator[dict[str, Any]]:
    """Stream JSON event objects from a local GH Archive .json.gz or .jsonl file."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def extract_agent_events(events: Iterator[dict[str, Any]]) -> Iterator[AgentEventRecord]:
    """Yield AgentEventRecord items for PushEvent and PullRequestEvent payloads."""
    for event in events:
        event_type = event.get("type", "")
        payload = event.get("payload") or {}
        messages: list[str] = []

        if event_type == "PushEvent":
            for commit in payload.get("commits") or []:
                msg = commit.get("message")
                if msg:
                    messages.append(msg)
        elif event_type == "PullRequestEvent":
            pr = payload.get("pull_request") or {}
            for field in (pr.get("title"), pr.get("body")):
                if field:
                    messages.append(field)
        else:
            continue

        detected: list[AgentSignal] = []
        for msg in messages:
            detected.extend(detect_commit_signals(msg))

        if detected:
            repo = (event.get("repo") or {}).get("name", "")
            yield AgentEventRecord(
                event_id=str(event.get("id", "")),
                event_type=event_type,
                repo_name=repo,
                created_at=str(event.get("created_at", "")),
                signals=tuple(detected),
            )
