"""MCP server for Jira and Confluence.

Implements the Model Context Protocol using the official ``mcp`` SDK over
stdio. Exposes tools for read and write operations on Jira issues and
Confluence pages.
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import JiraConfluenceClient

logger = logging.getLogger(__name__)

# Tool definitions
TOOLS: list[Tool] = [
    Tool(
        name="jira_get_issue",
        description="Get a Jira issue by key (e.g. 'PROJ-123')",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g. 'PROJ-123')",
                }
            },
            "required": ["issue_key"],
        },
    ),
    Tool(
        name="jira_search",
        description="Search Jira issues using JQL",
        inputSchema={
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "JQL query string",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 50,
                },
            },
            "required": ["jql"],
        },
    ),
    Tool(
        name="jira_add_comment",
        description="Add a comment to a Jira issue",
        inputSchema={
            "type": "object",
            "properties": {
                "issue_key": {"type": "string"},
                "comment": {"type": "string"},
            },
            "required": ["issue_key", "comment"],
        },
    ),
    Tool(
        name="confluence_get_page",
        description="Get a Confluence page by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Confluence page ID",
                },
                "expand": {
                    "type": "string",
                    "description": "Fields to expand (default: body.storage,version)",
                    "default": "body.storage,version",
                },
            },
            "required": ["page_id"],
        },
    ),
    Tool(
        name="confluence_update_page",
        description="Update an existing Confluence page",
        inputSchema={
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "title": {"type": "string"},
                "body": {
                    "type": "string",
                    "description": "Page content in Confluence Storage Format (XHTML)",
                },
            },
            "required": ["page_id", "title", "body"],
        },
    ),
    Tool(
        name="confluence_create_page",
        description="Create a new Confluence page",
        inputSchema={
            "type": "object",
            "properties": {
                "space_key": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "parent_id": {
                    "type": "string",
                    "description": "Optional parent page ID",
                },
            },
            "required": ["space_key", "title", "body"],
        },
    ),
]


def create_server() -> Server:
    """Create and configure the MCP server."""
    server: Server = Server("mcp-jira-confluence")
    client = JiraConfluenceClient()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Dispatch tool calls to client methods."""
        try:
            if name == "jira_get_issue":
                result = client.get_issue(arguments["issue_key"])
            elif name == "jira_search":
                result = client.search_issues(
                    arguments["jql"],
                    limit=arguments.get("limit", 50),
                )
            elif name == "jira_add_comment":
                result = client.add_comment(
                    arguments["issue_key"],
                    arguments["comment"],
                )
            elif name == "confluence_get_page":
                result = client.get_page(
                    arguments["page_id"],
                    expand=arguments.get("expand", "body.storage,version"),
                )
            elif name == "confluence_update_page":
                result = client.update_page(
                    arguments["page_id"],
                    arguments["title"],
                    arguments["body"],
                )
            elif name == "confluence_create_page":
                result = client.create_page(
                    arguments["space_key"],
                    arguments["title"],
                    arguments["body"],
                    parent_id=arguments.get("parent_id"),
                )
            else:
                raise ValueError(f"Unknown tool: {name}")

            return [TextContent(type="text", text=json.dumps(result, default=str, ensure_ascii=False))]

        except Exception as e:
            logger.exception("Tool %s failed", name)
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"error": str(e), "type": type(e).__name__}),
                )
            ]

    return server


async def _run() -> None:
    """Run the server on stdio."""
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """Entry point for `mcp-jira-confluence` command."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_run())


if __name__ == "__main__":
    main()
