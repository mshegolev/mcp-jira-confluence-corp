"""Jira tools exposed by the MCP server.

Every tool:
- Accepts a single Pydantic input model (defined in :mod:`models`)
- Returns a ``str`` (markdown or JSON, controlled by ``response_format``)
- Uses :class:`JiraConfluenceClient` for I/O
- Is registered against the shared FastMCP instance via :func:`register_jira_tools`
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .client import JiraConfluenceClient
from .models import (
    JiraAgileBoardsInput,
    JiraAssignInput,
    JiraBoardSprintsInput,
    JiraCommentInput,
    JiraCreateIssueInput,
    JiraIssueKey,
    JiraMyIssuesInput,
    JiraPagedInput,
    JiraProjectKey,
    JiraSearchInput,
    JiraSprintIssuesInput,
    JiraSummarizeInput,
    JiraTransitionInput,
    JiraUpdateIssueInput,
    JiraUserInput,
    ResponseFormat,
)
from .utils import (
    format_response,
    handle_error,
    paginate_list,
    render_issue_list_markdown,
    render_issue_markdown,
    render_simple_list_markdown,
)


def register_jira_tools(mcp: FastMCP, client: JiraConfluenceClient) -> None:
    """Register every Jira tool with the FastMCP server instance."""

    # ------------------------------------------------------------------
    # Read-only tools
    # ------------------------------------------------------------------

    @mcp.tool(
        name="jira_get_issue",
        annotations={
            "title": "Get Jira Issue",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_get_issue(params: JiraIssueKey) -> str:
        """Fetch a Jira issue by key, returning its core fields and description.

        Args:
            params: Validated :class:`JiraIssueKey` with ``issue_key`` and
                ``response_format``.

        Returns:
            A markdown summary (default) or JSON dump of the full Jira issue
            payload. On error, a human-readable error string.
        """
        try:
            issue = client.get_issue(params.issue_key)
            return format_response(issue, params.response_format, render_issue_markdown)
        except Exception as exc:
            return handle_error(f"get_issue({params.issue_key})", exc)

    @mcp.tool(
        name="jira_search_issues",
        annotations={
            "title": "Search Jira Issues",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_search_issues(params: JiraSearchInput) -> str:
        """Search Jira issues with a JQL query.

        Supports pagination via ``offset`` and ``limit``. Returns a paginated
        result with ``total``, ``count``, ``has_more``, ``next_offset``, and
        ``items``.
        """
        try:
            data = client.search_issues(
                params.jql,
                limit=params.limit,
                start=params.offset,
                fields=params.fields,
            )
            issues = data.get("issues", [])
            total = data.get("total", len(issues))
            payload = paginate_list(issues, params.limit, params.offset, total=total)
            return format_response(
                payload,
                params.response_format,
                lambda d: render_issue_list_markdown(d, f"Issues matching `{params.jql}`"),
            )
        except Exception as exc:
            return handle_error("search_issues", exc)

    @mcp.tool(
        name="jira_get_issue_comments",
        annotations={
            "title": "List Issue Comments",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_get_issue_comments(params: JiraIssueKey) -> str:
        """Return all comments on a Jira issue."""
        try:
            comments = client.get_issue_comments(params.issue_key)
            payload = {"issue_key": params.issue_key, "count": len(comments), "comments": comments}
            return format_response(
                payload,
                params.response_format,
                lambda d: "\n".join(
                    [f"# Comments on {params.issue_key}", "", f"Count: {d['count']}", ""]
                    + [
                        f"- **{(c.get('author') or {}).get('displayName', '?')}** at {c.get('created', '?')}:\n  {c.get('body', '')}"
                        for c in d["comments"]
                    ]
                ),
            )
        except Exception as exc:
            return handle_error(f"get_issue_comments({params.issue_key})", exc)

    @mcp.tool(
        name="jira_get_issue_transitions",
        annotations={
            "title": "List Available Transitions",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_get_issue_transitions(params: JiraIssueKey) -> str:
        """List workflow transitions currently available for an issue."""
        try:
            transitions = client.get_issue_transitions(params.issue_key)
            payload = {"issue_key": params.issue_key, "transitions": transitions}
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(
                    d["transitions"], f"Transitions for {params.issue_key}", ["id", "name"]
                ),
            )
        except Exception as exc:
            return handle_error(f"get_issue_transitions({params.issue_key})", exc)

    @mcp.tool(
        name="jira_get_issue_changelog",
        annotations={
            "title": "Get Issue Changelog",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_get_issue_changelog(params: JiraIssueKey) -> str:
        """Return the change history of a Jira issue."""
        try:
            history = client.get_issue_changelog(params.issue_key)
            payload = {"issue_key": params.issue_key, "count": len(history), "history": history}
            return format_response(payload, params.response_format)
        except Exception as exc:
            return handle_error(f"get_issue_changelog({params.issue_key})", exc)

    @mcp.tool(
        name="jira_list_projects",
        annotations={
            "title": "List Jira Projects",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_list_projects(params: JiraPagedInput) -> str:
        """List all accessible Jira projects."""
        try:
            projects = client.list_projects() or []
            payload = paginate_list(projects, params.limit, params.offset, total=len(projects))
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(d["items"], "Jira Projects", ["key", "name"]),
            )
        except Exception as exc:
            return handle_error("list_projects", exc)

    @mcp.tool(
        name="jira_get_project",
        annotations={
            "title": "Get Jira Project",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_get_project(params: JiraProjectKey) -> str:
        """Get details of a Jira project by key."""
        try:
            project = client.get_project(params.project_key)
            return format_response(project, params.response_format)
        except Exception as exc:
            return handle_error(f"get_project({params.project_key})", exc)

    @mcp.tool(
        name="jira_get_user",
        annotations={
            "title": "Get Jira User",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_get_user(params: JiraUserInput) -> str:
        """Get a Jira user profile by username or accountId."""
        try:
            user = client.get_user(params.username)
            return format_response(user, params.response_format)
        except Exception as exc:
            return handle_error(f"get_user({params.username})", exc)

    @mcp.tool(
        name="jira_get_my_issues",
        annotations={
            "title": "Get My Assigned Issues",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_get_my_issues(params: JiraMyIssuesInput) -> str:
        """List issues currently assigned to the authenticated user."""
        try:
            data = client.get_my_issues(
                project_key=params.project_key,
                statuses=params.statuses,
                limit=params.limit,
                start=params.offset,
            )
            issues = data.get("issues", [])
            payload = paginate_list(issues, params.limit, params.offset, total=data.get("total", len(issues)))
            return format_response(
                payload,
                params.response_format,
                lambda d: render_issue_list_markdown(d, "My Assigned Issues"),
            )
        except Exception as exc:
            return handle_error("get_my_issues", exc)

    @mcp.tool(
        name="jira_summarize_issue",
        annotations={
            "title": "Summarize Jira Issue",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_summarize_issue(params: JiraSummarizeInput) -> str:
        """One-shot comprehensive summary: issue fields + comments + changelog + transitions.

        Use this instead of calling four separate tools when you need full
        context on an issue.
        """
        try:
            summary = client.summarize_issue(
                issue_key=params.issue_key,
                include_comments=params.include_comments,
                include_changelog=params.include_changelog,
                include_transitions=params.include_transitions,
                comment_limit=params.comment_limit,
            )
            return format_response(
                summary,
                params.response_format,
                lambda d: _render_summary_markdown(d, params.issue_key),
            )
        except Exception as exc:
            return handle_error(f"summarize_issue({params.issue_key})", exc)

    @mcp.tool(
        name="jira_list_agile_boards",
        annotations={
            "title": "List Agile Boards",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_list_agile_boards(params: JiraAgileBoardsInput) -> str:
        """List Scrum/Kanban boards, optionally filtered by project or type."""
        try:
            data = client.list_agile_boards(
                project_key=params.project_key,
                board_type=params.board_type,
                limit=params.limit,
                start=params.offset,
            )
            boards = data.get("values", []) if isinstance(data, dict) else (data or [])
            total = data.get("total", len(boards)) if isinstance(data, dict) else len(boards)
            payload = paginate_list(boards, params.limit, params.offset, total=total)
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(d["items"], "Agile Boards", ["id", "name", "type"]),
            )
        except Exception as exc:
            return handle_error("list_agile_boards", exc)

    @mcp.tool(
        name="jira_list_board_sprints",
        annotations={
            "title": "List Board Sprints",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_list_board_sprints(params: JiraBoardSprintsInput) -> str:
        """List sprints for an agile board, filtered by state."""
        try:
            data = client.list_board_sprints(
                board_id=params.board_id,
                state=params.state.value,
                limit=params.limit,
                start=params.offset,
            )
            sprints = data.get("values", []) if isinstance(data, dict) else (data or [])
            total = data.get("total", len(sprints)) if isinstance(data, dict) else len(sprints)
            payload = paginate_list(sprints, params.limit, params.offset, total=total)
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(
                    d["items"], f"Sprints (state={params.state.value})", ["id", "name", "state"]
                ),
            )
        except Exception as exc:
            return handle_error(f"list_board_sprints({params.board_id})", exc)

    @mcp.tool(
        name="jira_list_sprint_issues",
        annotations={
            "title": "List Sprint Issues",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_list_sprint_issues(params: JiraSprintIssuesInput) -> str:
        """List all issues in a given sprint."""
        try:
            data = client.list_sprint_issues(
                sprint_id=params.sprint_id, limit=params.limit, start=params.offset
            )
            issues = data.get("issues", []) if isinstance(data, dict) else (data or [])
            total = data.get("total", len(issues)) if isinstance(data, dict) else len(issues)
            payload = paginate_list(issues, params.limit, params.offset, total=total)
            return format_response(
                payload,
                params.response_format,
                lambda d: render_issue_list_markdown(d, f"Sprint {params.sprint_id} Issues"),
            )
        except Exception as exc:
            return handle_error(f"list_sprint_issues({params.sprint_id})", exc)

    # ------------------------------------------------------------------
    # Write tools
    # ------------------------------------------------------------------

    @mcp.tool(
        name="jira_create_issue",
        annotations={
            "title": "Create Jira Issue",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def jira_create_issue(params: JiraCreateIssueInput) -> str:
        """Create a new Jira issue.

        Required: ``project_key`` and ``summary``. Additional fields can be
        provided via ``extra_fields`` (keyed by Jira API field name).
        """
        try:
            fields: dict = {
                "project": {"key": params.project_key},
                "summary": params.summary,
                "issuetype": {"name": params.issue_type},
            }
            if params.description:
                fields["description"] = params.description
            if params.assignee:
                fields["assignee"] = {"name": params.assignee}
            if params.priority:
                fields["priority"] = {"name": params.priority}
            if params.labels:
                fields["labels"] = params.labels
            if params.extra_fields:
                fields.update(params.extra_fields)

            issue = client.create_issue(fields)
            return format_response(issue, ResponseFormat.JSON)
        except Exception as exc:
            return handle_error("create_issue", exc)

    @mcp.tool(
        name="jira_update_issue",
        annotations={
            "title": "Update Jira Issue Fields",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_update_issue(params: JiraUpdateIssueInput) -> str:
        """Update fields on an existing Jira issue."""
        try:
            client.update_issue(params.issue_key, params.fields)
            return format_response(
                {"status": "updated", "issue_key": params.issue_key, "fields": params.fields},
                ResponseFormat.JSON,
            )
        except Exception as exc:
            return handle_error(f"update_issue({params.issue_key})", exc)

    @mcp.tool(
        name="jira_add_comment",
        annotations={
            "title": "Add Issue Comment",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def jira_add_comment(params: JiraCommentInput) -> str:
        """Add a comment to a Jira issue."""
        try:
            result = client.add_comment(params.issue_key, params.comment)
            return format_response(result, ResponseFormat.JSON)
        except Exception as exc:
            return handle_error(f"add_comment({params.issue_key})", exc)

    @mcp.tool(
        name="jira_transition_issue",
        annotations={
            "title": "Transition Issue",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def jira_transition_issue(params: JiraTransitionInput) -> str:
        """Move a Jira issue through its workflow by transition name.

        Transition names are case-insensitive. If the name doesn't match an
        available transition, the error message will list the valid options.
        """
        try:
            result = client.transition_issue(
                params.issue_key, params.transition_name, params.comment
            )
            return format_response(result, ResponseFormat.JSON)
        except Exception as exc:
            return handle_error(f"transition_issue({params.issue_key})", exc)

    @mcp.tool(
        name="jira_assign_issue",
        annotations={
            "title": "Assign Jira Issue",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def jira_assign_issue(params: JiraAssignInput) -> str:
        """Assign or unassign a Jira issue.

        Pass ``assignee=null`` to remove the current assignee.
        """
        try:
            client.assign_issue(params.issue_key, params.assignee)
            return format_response(
                {"status": "assigned", "issue_key": params.issue_key, "assignee": params.assignee},
                ResponseFormat.JSON,
            )
        except Exception as exc:
            return handle_error(f"assign_issue({params.issue_key})", exc)


def _render_summary_markdown(data: dict, issue_key: str) -> str:
    """Render a comprehensive issue summary as markdown."""
    issue = data.get("issue", {})
    parts = [render_issue_markdown(issue)]

    comments = data.get("comments")
    if comments:
        parts.append("")
        parts.append(f"## Comments ({len(comments)})")
        for c in comments:
            author = (c.get("author") or {}).get("displayName", "?")
            parts.append(f"- **{author}** ({c.get('created', '?')}): {c.get('body', '')}")

    transitions = data.get("transitions")
    if transitions:
        parts.append("")
        parts.append("## Available Transitions")
        for t in transitions:
            parts.append(f"- {t.get('name', '?')} (→ {(t.get('to') or {}).get('name', '?')})")

    history = data.get("changelog")
    if history:
        parts.append("")
        parts.append(f"## Changelog ({len(history)} entries)")
        for h in history[:10]:
            author = (h.get("author") or {}).get("displayName", "?")
            parts.append(f"- {h.get('created', '?')} by {author}")

    return "\n".join(parts)
