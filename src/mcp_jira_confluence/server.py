"""FastMCP-based MCP server for Atlassian Jira and Confluence.

This module wires together the shared :class:`JiraConfluenceClient` with the
Jira and Confluence tool registrations and exposes the ``main`` entry point
used by the ``mcp-jira-confluence-corp`` console script.

stdio is the default transport. To run over HTTP set the
``MCP_TRANSPORT=streamable_http`` environment variable.
"""

from __future__ import annotations

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .client import JiraConfluenceClient
from .confluence_tools import register_confluence_tools
from .jira_tools import register_jira_tools

# stdio servers must NOT log to stdout — the SDK uses stdout for the protocol.
logging.basicConfig(
    level=os.getenv("MCP_LOG_LEVEL", "INFO"),
    stream=sys.stderr,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mcp_jira_confluence")


def create_server() -> FastMCP:
    """Build and configure the FastMCP server, registering all tools."""
    mcp = FastMCP("jira_confluence_mcp")
    client = JiraConfluenceClient()
    register_jira_tools(mcp, client)
    register_confluence_tools(mcp, client)
    return mcp


def main() -> None:
    """Console-script entry point: run the server with the configured transport."""
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    mcp = create_server()

    logger.info("Starting jira_confluence_mcp with transport=%s", transport)

    if transport == "streamable_http":
        port = int(os.getenv("MCP_HTTP_PORT", "8000"))
        host = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
        mcp.run(transport="streamable_http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
