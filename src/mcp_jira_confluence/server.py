#!/usr/bin/env python3
"""
MCP server for Jira and Confluence with MTS proxy support.

Run with: mcp-jira-confluence
or: python -m mcp_jira_confluence.server
"""

import json
import sys
from typing import Any

from .client import JiraConfluenceClient


class JiraConfluenceMCPServer:
    """MCP server implementation for Jira/Confluence."""

    def __init__(self):
        """Initialize MCP server."""
        self.client = JiraConfluenceClient()

    def handle_jira_get_issue(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle jira/get_issue tool call."""
        issue_key = params["issue_key"]
        try:
            issue = self.client.get_issue(issue_key)
            return {"status": "success", "issue": issue}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_jira_search(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle jira/search tool call."""
        jql = params["jql"]
        limit = params.get("limit", 50)
        try:
            issues = self.client.search_issues(jql, limit=limit)
            return {"status": "success", "issues": issues}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_confluence_get_page(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle confluence/get_page tool call."""
        page_id = params["page_id"]
        try:
            page = self.client.get_page(page_id)
            return {"status": "success", "page": page}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def handle_confluence_update_page(self, params: dict[str, Any]) -> dict[str, Any]:
        """Handle confluence/update_page tool call."""
        page_id = params["page_id"]
        title = params["title"]
        body = params["body"]
        try:
            result = self.client.update_page(page_id, title, body)
            return {"status": "success", "page": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def process_tool_call(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Process a tool call."""
        handlers = {
            "jira/get_issue": self.handle_jira_get_issue,
            "jira/search": self.handle_jira_search,
            "confluence/get_page": self.handle_confluence_get_page,
            "confluence/update_page": self.handle_confluence_update_page,
        }

        handler = handlers.get(tool_name)
        if handler is None:
            return {"status": "error", "message": f"Unknown tool: {tool_name}"}

        return handler(params)

    def run(self):
        """Run MCP server (stdio mode)."""
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    break

                request = json.loads(line)
                tool_name = request.get("tool")
                params = request.get("params", {})

                result = self.process_tool_call(tool_name, params)
                print(json.dumps(result))
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                print(json.dumps({"status": "error", "message": f"Invalid JSON: {e}"}))
                sys.stdout.flush()
            except Exception as e:
                print(json.dumps({"status": "error", "message": str(e)}))
                sys.stdout.flush()


def main():
    """Entry point."""
    server = JiraConfluenceMCPServer()
    server.run()


if __name__ == "__main__":
    main()
