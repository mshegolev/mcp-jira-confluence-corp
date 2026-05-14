"""Unified client for Jira and Confluence with corporate proxy support."""

import os
from typing import Any, Optional

from atlassian import Confluence, Jira

from .config import ConfluenceConfig, JiraConfig, ProxyConfig


class JiraConfluenceClient:
    """Unified client for the Jira and Confluence REST APIs.

    Designed for corporate networks where system proxies and self-signed
    certificates interfere with API access. On construction the client clears
    ``HTTP_PROXY``-style environment variables so the underlying ``requests``
    session connects directly to the configured Atlassian hosts.

    Args:
        jira_config: Jira connection config. Loaded from environment if ``None``.
        confluence_config: Confluence connection config. Loaded from environment
            if ``None``.
        proxy_config: Proxy bypass configuration. Defaults to reading
            ``MCP_BYPASS_DOMAINS`` from the environment.
    """

    def __init__(
        self,
        jira_config: Optional[JiraConfig] = None,
        confluence_config: Optional[ConfluenceConfig] = None,
        proxy_config: Optional[ProxyConfig] = None,
    ):
        self.jira_config = jira_config or JiraConfig.from_env()
        self.confluence_config = confluence_config or ConfluenceConfig.from_env()
        self.proxy_config = proxy_config or ProxyConfig()

        self._clear_proxy_env()

        self._jira: Optional[Jira] = None
        self._confluence: Optional[Confluence] = None

    @staticmethod
    def _clear_proxy_env() -> None:
        """Clear HTTP proxy environment variables.

        Prevents global proxy settings (e.g. an SSH tunnel for a different
        service) from intercepting traffic to internal Atlassian hosts.
        """
        for var in (
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "http_proxy",
            "https_proxy",
            "ALL_PROXY",
            "all_proxy",
        ):
            os.environ.pop(var, None)

    @property
    def jira(self) -> Jira:
        """Lazily construct and return the underlying ``atlassian.Jira`` client."""
        if self._jira is None:
            self._jira = Jira(
                url=self.jira_config.url,
                verify_ssl=self.proxy_config.verify_ssl,
                **self.jira_config.get_auth_dict(),
            )
        return self._jira

    @property
    def confluence(self) -> Confluence:
        """Lazily construct and return the underlying ``atlassian.Confluence`` client."""
        if self._confluence is None:
            self._confluence = Confluence(
                url=self.confluence_config.url,
                verify_ssl=self.proxy_config.verify_ssl,
                **self.confluence_config.get_auth_dict(),
            )
        return self._confluence

    # ------------------------------------------------------------------
    # Jira methods
    # ------------------------------------------------------------------
    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """Get a Jira issue by key."""
        return self.jira.issue(issue_key)

    def search_issues(self, jql: str, limit: int = 50) -> dict[str, Any]:
        """Search Jira issues using a JQL query."""
        return self.jira.jql(jql, limit=limit)

    def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a new Jira issue."""
        return self.jira.create_issue(fields=fields)

    def update_issue(self, issue_key: str, fields: dict[str, Any]) -> None:
        """Update an existing Jira issue."""
        self.jira.update_issue(issue_key, fields=fields)

    def add_comment(self, issue_key: str, comment: str) -> dict[str, Any]:
        """Add a comment to a Jira issue."""
        return self.jira.add_comment(issue_key, comment)

    # ------------------------------------------------------------------
    # Confluence methods
    # ------------------------------------------------------------------
    def get_page(self, page_id: str, expand: str = "body.storage,version") -> dict[str, Any]:
        """Get a Confluence page by ID."""
        return self.confluence.get_page_by_id(page_id, expand=expand)

    def get_page_by_title(
        self, title: str, space_key: str, expand: str = "body.storage,version"
    ) -> dict[str, Any]:
        """Get a Confluence page by title and space key."""
        return self.confluence.get_page_by_title(space_key, title, expand=expand)

    def create_page(
        self,
        space_key: str,
        title: str,
        body: str,
        parent_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create a new Confluence page in the given space."""
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
    ) -> dict[str, Any]:
        """Update an existing Confluence page."""
        return self.confluence.update_page(
            page_id=page_id,
            title=title,
            body=body,
        )

    def add_page_label(self, page_id: str, label: str) -> None:
        """Add a label to a Confluence page."""
        self.confluence.set_page_label(page_id, label)

    def delete_page(self, page_id: str) -> None:
        """Delete a Confluence page."""
        self.confluence.remove_page(page_id)
