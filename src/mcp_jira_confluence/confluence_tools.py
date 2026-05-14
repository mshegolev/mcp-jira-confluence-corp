"""Confluence tools exposed by the MCP server."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .client import JiraConfluenceClient
from .models import (
    ConfluenceCreatePageInput,
    ConfluenceLabelInput,
    ConfluenceListSpacesInput,
    ConfluencePageAttachmentsInput,
    ConfluencePageChildrenInput,
    ConfluencePageCommentInput,
    ConfluencePageHistoryInput,
    ConfluencePageIdInput,
    ConfluencePageTitleInput,
    ConfluenceSearchInput,
    ConfluenceUpdatePageInput,
    ResponseFormat,
)
from .utils import (
    format_response,
    handle_error,
    paginate_list,
    render_page_markdown,
    render_simple_list_markdown,
)


def register_confluence_tools(mcp: FastMCP, client: JiraConfluenceClient) -> None:
    """Register every Confluence tool with the FastMCP server instance."""

    # ------------------------------------------------------------------
    # Read-only tools
    # ------------------------------------------------------------------

    @mcp.tool(
        name="confluence_get_page",
        annotations={
            "title": "Get Confluence Page by ID",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_get_page(params: ConfluencePageIdInput) -> str:
        """Fetch a Confluence page by ID.

        Returns the page metadata plus its body in Confluence Storage Format
        (XHTML) by default.
        """
        try:
            page = client.get_page(params.page_id, expand=params.expand)
            return format_response(page, params.response_format, render_page_markdown)
        except Exception as exc:
            return handle_error(f"get_page({params.page_id})", exc)

    @mcp.tool(
        name="confluence_get_page_by_title",
        annotations={
            "title": "Get Page by Title",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_get_page_by_title(params: ConfluencePageTitleInput) -> str:
        """Fetch a Confluence page by exact title within a space."""
        try:
            page = client.get_page_by_title(params.title, params.space_key, expand=params.expand)
            return format_response(page, params.response_format, render_page_markdown)
        except Exception as exc:
            return handle_error(f"get_page_by_title({params.title}@{params.space_key})", exc)

    @mcp.tool(
        name="confluence_search",
        annotations={
            "title": "Search Confluence (CQL)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_search(params: ConfluenceSearchInput) -> str:
        """Search Confluence using Confluence Query Language (CQL).

        Example queries:
            - ``space = DOC AND type = page AND title ~ "release"``
            - ``label = "team-alpha"``
            - ``contributor = "alice" AND lastmodified > now("-30d")``
        """
        try:
            data = client.search_cql(params.cql, limit=params.limit, start=params.offset)
            results = data.get("results", []) if isinstance(data, dict) else (data or [])
            total = data.get("totalSize", data.get("size", len(results))) if isinstance(data, dict) else len(results)
            payload = paginate_list(results, params.limit, params.offset, total=total)
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(
                    [
                        {
                            "title": (r.get("content") or r).get("title", "?"),
                            "id": (r.get("content") or r).get("id", "?"),
                            "type": (r.get("content") or r).get("type", "?"),
                        }
                        for r in d["items"]
                    ],
                    f"CQL: `{params.cql}`",
                    ["title", "id", "type"],
                ),
            )
        except Exception as exc:
            return handle_error("search_cql", exc)

    @mcp.tool(
        name="confluence_get_page_children",
        annotations={
            "title": "List Page Children",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_get_page_children(params: ConfluencePageChildrenInput) -> str:
        """List child pages of a Confluence page."""
        try:
            children = client.get_page_children(
                params.page_id, limit=params.limit, start=params.offset
            )
            items = children if isinstance(children, list) else children.get("results", [])
            payload = paginate_list(items, params.limit, params.offset, total=len(items))
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(
                    d["items"], f"Children of page {params.page_id}", ["id", "title"]
                ),
            )
        except Exception as exc:
            return handle_error(f"get_page_children({params.page_id})", exc)

    @mcp.tool(
        name="confluence_get_page_comments",
        annotations={
            "title": "List Page Comments",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_get_page_comments(params: ConfluencePageIdInput) -> str:
        """List comments on a Confluence page."""
        try:
            comments = client.get_page_comments(params.page_id)
            payload = {"page_id": params.page_id, "count": len(comments), "comments": comments}
            return format_response(payload, params.response_format)
        except Exception as exc:
            return handle_error(f"get_page_comments({params.page_id})", exc)

    @mcp.tool(
        name="confluence_get_page_labels",
        annotations={
            "title": "List Page Labels",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_get_page_labels(params: ConfluencePageIdInput) -> str:
        """List labels applied to a Confluence page."""
        try:
            labels = client.get_page_labels(params.page_id)
            payload = {"page_id": params.page_id, "count": len(labels), "labels": labels}
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(
                    d["labels"], f"Labels on page {params.page_id}", ["name"]
                ),
            )
        except Exception as exc:
            return handle_error(f"get_page_labels({params.page_id})", exc)

    @mcp.tool(
        name="confluence_list_spaces",
        annotations={
            "title": "List Confluence Spaces",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_list_spaces(params: ConfluenceListSpacesInput) -> str:
        """List Confluence spaces, optionally filtered by type ('global'/'personal')."""
        try:
            data = client.list_spaces(
                limit=params.limit, start=params.offset, space_type=params.space_type
            )
            spaces = data.get("results", []) if isinstance(data, dict) else (data or [])
            total = data.get("size", len(spaces)) if isinstance(data, dict) else len(spaces)
            payload = paginate_list(spaces, params.limit, params.offset, total=total)
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(
                    d["items"], "Confluence Spaces", ["key", "name", "type"]
                ),
            )
        except Exception as exc:
            return handle_error("list_spaces", exc)

    @mcp.tool(
        name="confluence_get_page_history",
        annotations={
            "title": "Get Page Version History",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_get_page_history(params: ConfluencePageHistoryInput) -> str:
        """Return version history info for a Confluence page."""
        try:
            history = client.get_page_history(params.page_id)
            return format_response(history, params.response_format)
        except Exception as exc:
            return handle_error(f"get_page_history({params.page_id})", exc)

    @mcp.tool(
        name="confluence_get_page_attachments",
        annotations={
            "title": "List Page Attachments",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_get_page_attachments(params: ConfluencePageAttachmentsInput) -> str:
        """List attachments on a Confluence page."""
        try:
            attachments = client.get_page_attachments(params.page_id)
            payload = paginate_list(
                attachments, params.limit, params.offset, total=len(attachments)
            )
            return format_response(
                payload,
                params.response_format,
                lambda d: render_simple_list_markdown(
                    d["items"], f"Attachments on page {params.page_id}", ["title", "id"]
                ),
            )
        except Exception as exc:
            return handle_error(f"get_page_attachments({params.page_id})", exc)

    # ------------------------------------------------------------------
    # Write tools
    # ------------------------------------------------------------------

    @mcp.tool(
        name="confluence_create_page",
        annotations={
            "title": "Create Confluence Page",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def confluence_create_page(params: ConfluenceCreatePageInput) -> str:
        """Create a new Confluence page.

        ``body`` must be in Confluence Storage Format (XHTML). To create a
        child page, pass ``parent_id``.
        """
        try:
            page = client.create_page(
                space_key=params.space_key,
                title=params.title,
                body=params.body,
                parent_id=params.parent_id,
            )
            return format_response(page, ResponseFormat.JSON)
        except Exception as exc:
            return handle_error(f"create_page({params.title}@{params.space_key})", exc)

    @mcp.tool(
        name="confluence_update_page",
        annotations={
            "title": "Update Confluence Page",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_update_page(params: ConfluenceUpdatePageInput) -> str:
        """Update an existing Confluence page (full replacement of body)."""
        try:
            page = client.update_page(
                page_id=params.page_id, title=params.title, body=params.body
            )
            return format_response(page, ResponseFormat.JSON)
        except Exception as exc:
            return handle_error(f"update_page({params.page_id})", exc)

    @mcp.tool(
        name="confluence_add_comment",
        annotations={
            "title": "Add Page Comment",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": False,
            "openWorldHint": True,
        },
    )
    async def confluence_add_comment(params: ConfluencePageCommentInput) -> str:
        """Add a comment to a Confluence page."""
        try:
            result = client.add_page_comment(params.page_id, params.comment)
            return format_response(result, ResponseFormat.JSON)
        except Exception as exc:
            return handle_error(f"add_page_comment({params.page_id})", exc)

    @mcp.tool(
        name="confluence_add_label",
        annotations={
            "title": "Add Page Label",
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_add_label(params: ConfluenceLabelInput) -> str:
        """Add a label to a Confluence page."""
        try:
            client.add_page_label(params.page_id, params.label)
            return format_response(
                {"status": "added", "page_id": params.page_id, "label": params.label},
                ResponseFormat.JSON,
            )
        except Exception as exc:
            return handle_error(f"add_page_label({params.page_id}, {params.label})", exc)

    @mcp.tool(
        name="confluence_remove_label",
        annotations={
            "title": "Remove Page Label",
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": True,
            "openWorldHint": True,
        },
    )
    async def confluence_remove_label(params: ConfluenceLabelInput) -> str:
        """Remove a label from a Confluence page."""
        try:
            client.remove_page_label(params.page_id, params.label)
            return format_response(
                {"status": "removed", "page_id": params.page_id, "label": params.label},
                ResponseFormat.JSON,
            )
        except Exception as exc:
            return handle_error(f"remove_page_label({params.page_id}, {params.label})", exc)
