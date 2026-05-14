"""Unified client for Jira and Confluence with MTS proxy support."""

import os
from typing import Any, Optional

import requests
from atlassian import Confluence, Jira

from .config import ProxyConfig, JiraConfig, ConfluenceConfig


class JiraConfluenceClient:
    """
    Unified client for Jira and Confluence APIs with MTS proxy support.

    Features:
    - Automatic proxy bypass for internal MTS domains
    - Self-signed certificate handling
    - Token and username/password auth
    """

    def __init__(
        self,
        jira_config: Optional[JiraConfig] = None,
        confluence_config: Optional[ConfluenceConfig] = None,
        proxy_config: Optional[ProxyConfig] = None,
    ):
        """
        Initialize Jira/Confluence client.

        Args:
            jira_config: Jira connection config (loaded from env if None)
            confluence_config: Confluence connection config (loaded from env if None)
            proxy_config: Proxy configuration (default: MTS proxy)
        """
        self.jira_config = jira_config or JiraConfig.from_env()
        self.confluence_config = confluence_config or ConfluenceConfig.from_env()
        self.proxy_config = proxy_config or ProxyConfig()

        # Clear global proxy env vars (they interfere with internal MTS domains)
        self._clear_proxy_env()

        # Initialize clients
        self._jira: Optional[Jira] = None
        self._confluence: Optional[Confluence] = None

    def _clear_proxy_env(self) -> None:
        """Clear HTTP_PROXY env vars to avoid interfering with internal MTS domains."""
        for var in [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "http_proxy",
            "https_proxy",
            "ALL_PROXY",
            "all_proxy",
        ]:
            if var in os.environ:
                del os.environ[var]

    @property
    def jira(self) -> Jira:
        """Get or create Jira client."""
        if self._jira is None:
            auth = self.jira_config.get_auth_dict()
            self._jira = Jira(
                url=self.jira_config.url,
                verify_ssl=self.proxy_config.verify_ssl,
                **auth,
            )
        return self._jira

    @property
    def confluence(self) -> Confluence:
        """Get or create Confluence client."""
        if self._confluence is None:
            auth = self.confluence_config.get_auth_dict()
            self._confluence = Confluence(
                url=self.confluence_config.url,
                verify_ssl=self.proxy_config.verify_ssl,
                **auth,
            )
        return self._confluence

    # Jira methods
    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """Get Jira issue by key."""
        return self.jira.issue(issue_key)

    def get_issue_changelog(self, issue_key: str) -> list[dict]:
        """Get issue changelog."""
        issue = self.get_issue(issue_key)
        return issue.get("changelog", {}).get("histories", [])

    def search_issues(self, jql: str, limit: int = 50) -> list[dict]:
        """Search issues using JQL."""
        return self.jira.jql(jql, limit=limit)

    def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create new issue."""
        return self.jira.create_issue(fields=fields)

    def update_issue(self, issue_key: str, fields: dict[str, Any]) -> None:
        """Update issue."""
        self.jira.update_issue(issue_key, fields=fields)

    def add_comment(self, issue_key: str, comment: str) -> dict[str, Any]:
        """Add comment to issue."""
        return self.jira.add_comment(issue_key, comment)

    # Confluence methods
    def get_page(self, page_id: str, expand: str = "body.storage,version") -> dict[str, Any]:
        """Get Confluence page by ID."""
        return self.confluence.get_page_by_id(page_id, expand=expand)

    def get_page_by_title(
        self, title: str, space_key: str, expand: str = "body.storage,version"
    ) -> dict[str, Any]:
        """Get Confluence page by title and space."""
        return self.confluence.get_page_by_title(
            space_key, title, expand=expand
        )

    def search_pages(self, query: str, limit: int = 10) -> list[dict]:
        """Search Confluence pages."""
        return self.confluence.search_pages_by_label(query, limit=limit)

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create Confluence page."""
        return self.confluence.create_page(
            space=space_key,
            title=title,
            body=body,
            parent_id=parent_id,
        )

    def update_page(
        self,
        page_id: str,
        title: str,
        body: str,
        version_number: Optional[int] = None,
    ) -> dict[str, Any]:
        """Update Confluence page."""
        return self.confluence.update_page(
            page_id=page_id,
            title=title,
            body=body,
            version_number=version_number,
        )

    def add_page_label(self, page_id: str, label: str) -> None:
        """Add label to page."""
        self.confluence.set_page_label(page_id, label)

    def delete_page(self, page_id: str) -> None:
        """Delete Confluence page."""
        self.confluence.remove_page(page_id)
