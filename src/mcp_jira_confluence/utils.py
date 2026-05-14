"""Shared utilities for MCP tools: response formatting, pagination, errors."""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from .models import ResponseFormat


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def handle_error(operation: str, exc: Exception) -> str:
    """Return a clear, actionable error message for an MCP tool response.

    The message is intentionally human-readable and includes a suggestion when
    possible. We never expose tracebacks or internal stack frames.
    """
    err_type = type(exc).__name__
    text = str(exc) or err_type

    suggestions: dict[str, str] = {
        "HTTPError": "Check the resource ID and your permissions.",
        "ConnectionError": "Check your network connection and the configured *_URL.",
        "Timeout": "The server took too long to respond. Retry the operation.",
        "ApiPermissionError": "Authentication succeeded but the operation is not permitted.",
        "ApiNotFoundError": "Resource not found — verify the ID/key is correct.",
        "ApiValueError": "Invalid input — review the field requirements.",
    }
    suggestion = suggestions.get(err_type, "")

    parts = [f"Error during {operation}: {text}"]
    if suggestion:
        parts.append(f"Suggestion: {suggestion}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def paginate_list(
    items: list[Any],
    limit: int,
    offset: int,
    total: Optional[int] = None,
) -> dict[str, Any]:
    """Slice a list and return a structured pagination payload.

    Args:
        items: Either the full result list (we slice locally), or the already
            sliced page returned by the server.
        limit: Page size requested by the caller.
        offset: Starting offset requested by the caller.
        total: Total count if known. If ``None``, falls back to ``len(items)``.
    """
    total_count = total if total is not None else len(items)
    # If the caller already passed a page (len(items) <= limit) we don't reslice.
    if len(items) > limit:
        page = items[offset : offset + limit]
    else:
        page = items
    next_offset = offset + len(page) if offset + len(page) < total_count else None
    return {
        "total": total_count,
        "count": len(page),
        "offset": offset,
        "limit": limit,
        "has_more": next_offset is not None,
        "next_offset": next_offset,
        "items": page,
    }


# ---------------------------------------------------------------------------
# Response formatting
# ---------------------------------------------------------------------------

def format_response(
    data: Any,
    response_format: ResponseFormat,
    markdown_renderer: Optional[Callable[[Any], str]] = None,
) -> str:
    """Render a response in either JSON or Markdown form.

    If ``markdown_renderer`` is provided and the requested format is markdown,
    it is used to produce the markdown string. Otherwise we fall back to a
    pretty-printed JSON document inside a fenced code block.
    """
    if response_format == ResponseFormat.JSON:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    if markdown_renderer is not None:
        return markdown_renderer(data)

    rendered = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    return f"```json\n{rendered}\n```"


# ---------------------------------------------------------------------------
# Markdown helpers for common Atlassian shapes
# ---------------------------------------------------------------------------

def _safe(value: Any) -> str:
    return "—" if value in (None, "") else str(value)


def render_issue_markdown(issue: dict[str, Any]) -> str:
    """Render a Jira issue dict as a compact markdown summary."""
    fields = issue.get("fields", {}) or {}
    key = issue.get("key", "?")
    summary = fields.get("summary", "(no summary)")
    status = (fields.get("status") or {}).get("name")
    issuetype = (fields.get("issuetype") or {}).get("name")
    priority = (fields.get("priority") or {}).get("name")
    assignee_obj = fields.get("assignee") or {}
    reporter_obj = fields.get("reporter") or {}
    assignee = assignee_obj.get("displayName") or assignee_obj.get("name")
    reporter = reporter_obj.get("displayName") or reporter_obj.get("name")
    created = fields.get("created")
    updated = fields.get("updated")
    description = fields.get("description") or ""

    lines = [
        f"# {key}: {summary}",
        "",
        f"- **Type:** {_safe(issuetype)}",
        f"- **Status:** {_safe(status)}",
        f"- **Priority:** {_safe(priority)}",
        f"- **Assignee:** {_safe(assignee)}",
        f"- **Reporter:** {_safe(reporter)}",
        f"- **Created:** {_safe(created)}",
        f"- **Updated:** {_safe(updated)}",
    ]
    if description:
        lines.extend(["", "## Description", "", str(description)])
    return "\n".join(lines)


def render_issue_list_markdown(payload: dict[str, Any], title: str = "Issues") -> str:
    """Render a paginated issue list as markdown."""
    items = payload.get("items") or payload.get("issues") or []
    total = payload.get("total", len(items))
    lines = [f"# {title}", "", f"Total: {total}, showing {len(items)}", ""]
    for issue in items:
        fields = issue.get("fields", {}) or {}
        key = issue.get("key", "?")
        summary = fields.get("summary", "(no summary)")
        status = (fields.get("status") or {}).get("name", "?")
        assignee_obj = fields.get("assignee") or {}
        assignee = assignee_obj.get("displayName") or assignee_obj.get("name") or "Unassigned"
        lines.append(f"- **{key}** [{status}] — {summary} _(assignee: {assignee})_")
    if payload.get("has_more"):
        lines.extend(["", f"_More results available — pass `offset={payload.get('next_offset')}` to continue._"])
    return "\n".join(lines)


def render_page_markdown(page: dict[str, Any]) -> str:
    """Render a Confluence page dict as a markdown summary."""
    title = page.get("title", "(untitled)")
    page_id = page.get("id", "?")
    version = (page.get("version") or {}).get("number")
    space_key = (page.get("space") or {}).get("key")
    body = ((page.get("body") or {}).get("storage") or {}).get("value", "")

    lines = [
        f"# {title}",
        "",
        f"- **ID:** {page_id}",
        f"- **Space:** {_safe(space_key)}",
        f"- **Version:** {_safe(version)}",
    ]
    if body:
        lines.extend(["", "## Content (Confluence Storage Format)", "", body])
    return "\n".join(lines)


def render_simple_list_markdown(items: list[dict[str, Any]], title: str, keys: list[str]) -> str:
    """Render an arbitrary list of dicts as a markdown table-ish block."""
    lines = [f"# {title}", "", f"Count: {len(items)}", ""]
    for item in items:
        bullet = " · ".join(f"**{k}:** {_safe(item.get(k))}" for k in keys)
        lines.append(f"- {bullet}")
    return "\n".join(lines)
