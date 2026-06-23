"""High-level workflow tools that compose multiple API calls.

These exist because they save the agent multiple round-trips for very common
operations: extracting all the links out of an issue, or assembling a daily
standup picture of a sprint.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import JiraConfluenceClient
from .models import (
    JiraExtractLinksInput,
    JiraStandupSummaryInput,
)
from .utils import format_response, handle_error

# Regex patterns for link extraction
_URL_RE = re.compile(r"https?://[^\s\"'<>)]+", re.IGNORECASE)
_CONFLUENCE_RE = re.compile(
    r"https?://[^\s\"'<>)]*?(confluence|atlassian\.net/wiki)[^\s\"'<>)]*", re.IGNORECASE
)
_GIT_HOST_RE = re.compile(
    r"https?://([^/]*(github\.com|gitlab\.[^/]+|bitbucket\.org|dev\.azure\.com|azure\.com))[^\s\"'<>)]*",
    re.IGNORECASE,
)


def _classify(url: str) -> str:
    if _CONFLUENCE_RE.search(url):
        return "confluence"
    if _GIT_HOST_RE.search(url):
        return "git"
    return "other"


def _extract_text_links(text: str) -> set[str]:
    if not text:
        return set()
    return set(_URL_RE.findall(str(text)))


def register_workflow_tools(mcp: FastMCP, client: JiraConfluenceClient) -> None:
    """Register multi-step workflow tools."""

    @mcp.tool(
        name="jira_extract_links",
        annotations={
            "title": "Extract Confluence & Git Links from Issue",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_extract_links(params: JiraExtractLinksInput) -> str:
        """Find every Confluence, Git, or other URL referenced by a Jira issue.

        Scans the issue's description, optionally its comments, and (optionally)
        Jira's remote-issue-link entries. Returns links grouped by category:
        ``confluence``, ``git``, and ``other``.

        Use cases:
            - "What design docs are linked from PROJ-123?"
            - "Which repos does this story touch?"
        """
        try:
            issue = client.get_issue(params.issue_key)
            fields = issue.get("fields", {}) or {}

            buckets: dict[str, set[str]] = {"confluence": set(), "git": set(), "other": set()}
            sources: list[tuple[str, str]] = []  # (source_label, text)

            # Description
            desc = fields.get("description")
            if desc:
                sources.append(("description", str(desc)))

            # Comments
            if params.include_comments:
                comments = client.get_issue_comments(params.issue_key)
                for c in comments:
                    body = c.get("body", "")
                    author = (c.get("author") or {}).get("displayName", "?")
                    sources.append((f"comment by {author}", str(body)))

            # Remote links
            if params.include_remote_links:
                remote = client.get_remote_links(params.issue_key)
                for r in remote:
                    obj = r.get("object", {}) if isinstance(r, dict) else {}
                    url = obj.get("url")
                    if url:
                        buckets[_classify(url)].add(url)

            # Pull URLs out of text sources
            for _label, text in sources:
                for url in _extract_text_links(text):
                    buckets[_classify(url)].add(url)

            payload = {
                "issue_key": params.issue_key,
                "counts": {k: len(v) for k, v in buckets.items()},
                "links": {k: sorted(v) for k, v in buckets.items()},
            }

            def _md(d: dict) -> str:
                lines = [f"# Links in {d['issue_key']}", ""]
                for cat in ("confluence", "git", "other"):
                    urls = d["links"][cat]
                    lines.append(f"## {cat.capitalize()} ({len(urls)})")
                    if not urls:
                        lines.append("_none_")
                    else:
                        lines.extend(f"- {u}" for u in urls)
                    lines.append("")
                return "\n".join(lines).rstrip()

            return format_response(payload, params.response_format, _md)
        except Exception as exc:
            return handle_error(f"extract_links({params.issue_key})", exc)

    @mcp.tool(
        name="jira_daily_standup_summary",
        annotations={
            "title": "Daily Standup Summary",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_daily_standup_summary(params: JiraStandupSummaryInput) -> str:
        """Compile a daily-standup-style picture of a sprint in one call.

        Returns: sprint metadata, counts by status, blockers (issues with the
        'blocked' label or 'Blocked' status), and assignee workload.
        Either ``sprint_id`` or ``board_id`` must be supplied; if only
        ``board_id`` is given, the currently active sprint is used.
        """
        try:
            sprint_id = params.sprint_id
            sprint_info: dict[str, Any] = {}
            if sprint_id is None:
                if params.board_id is None:
                    return handle_error(
                        "daily_standup_summary",
                        ValueError("Either sprint_id or board_id must be provided"),
                    )
                sprint = client.get_active_sprint_for_board(params.board_id)
                if not sprint:
                    return handle_error(
                        "daily_standup_summary",
                        ValueError(f"No active sprint on board {params.board_id}"),
                    )
                sprint_id = sprint.get("id")
                sprint_info = sprint

            data = client.list_sprint_issues(sprint_id=int(sprint_id), limit=200, start=0)
            issues = data.get("issues", []) if isinstance(data, dict) else (data or [])
            total = data.get("total", len(issues)) if isinstance(data, dict) else len(issues)

            status_counter: Counter = Counter()
            assignee_counter: Counter = Counter()
            blockers: list[dict[str, Any]] = []

            for issue in issues:
                fields = issue.get("fields", {}) or {}
                status_name = (fields.get("status") or {}).get("name", "Unknown")
                status_counter[status_name] += 1

                assignee_obj = fields.get("assignee") or {}
                name = assignee_obj.get("displayName") or assignee_obj.get("name") or "Unassigned"
                assignee_counter[name] += 1

                labels = [str(label).lower() for label in (fields.get("labels") or [])]
                if status_name.lower() == "blocked" or "blocked" in labels or "blocker" in labels:
                    blockers.append(
                        {
                            "key": issue.get("key"),
                            "summary": fields.get("summary"),
                            "status": status_name,
                            "assignee": name,
                        }
                    )

            done_count = sum(
                n for s, n in status_counter.items() if s.lower() in {"done", "closed", "resolved"}
            )
            progress_pct = round(done_count / total * 100, 1) if total else 0.0

            payload = {
                "sprint_id": sprint_id,
                "sprint": sprint_info,
                "total_issues": total,
                "done": done_count,
                "progress_percent": progress_pct,
                "by_status": dict(status_counter),
                "by_assignee": dict(assignee_counter),
                "blockers": blockers,
            }

            def _md(d: dict) -> str:
                lines = [
                    f"# Standup — sprint {d['sprint_id']}",
                    "",
                    f"**Progress:** {d['done']}/{d['total_issues']} done ({d['progress_percent']}%)",
                    "",
                    "## By status",
                ]
                for status, n in sorted(d["by_status"].items(), key=lambda kv: -kv[1]):
                    lines.append(f"- {status}: {n}")
                lines.extend(["", "## Workload"])
                for who, n in sorted(d["by_assignee"].items(), key=lambda kv: -kv[1]):
                    lines.append(f"- {who}: {n}")
                if d["blockers"]:
                    lines.extend(["", f"## 🚧 Blockers ({len(d['blockers'])})"])
                    for b in d["blockers"]:
                        lines.append(
                            f"- **{b['key']}** [{b['status']}] — {b['summary']} _({b['assignee']})_"
                        )
                return "\n".join(lines)

            return format_response(payload, params.response_format, _md)
        except Exception as exc:
            return handle_error(f"daily_standup_summary(sprint={params.sprint_id})", exc)
