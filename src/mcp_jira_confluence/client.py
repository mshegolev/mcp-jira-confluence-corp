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
    def get_issue(
        self, issue_key: str, fields: Optional[list[str]] = None, expand: Optional[str] = None
    ) -> dict[str, Any]:
        """Get a Jira issue by key."""
        kwargs: dict[str, Any] = {}
        if fields is not None:
            kwargs["fields"] = ",".join(fields)
        if expand is not None:
            kwargs["expand"] = expand
        return self.jira.issue(issue_key, **kwargs)

    def search_issues(
        self,
        jql: str,
        limit: int = 50,
        start: int = 0,
        fields: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Search Jira issues using JQL.

        Returns the raw API payload including ``issues``, ``total``, etc.
        """
        kwargs: dict[str, Any] = {"limit": limit, "start": start}
        if fields is not None:
            kwargs["fields"] = ",".join(fields)
        return self.jira.jql(jql, **kwargs)

    def create_issue(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Create a new Jira issue."""
        return self.jira.create_issue(fields=fields)

    def update_issue(self, issue_key: str, fields: dict[str, Any]) -> None:
        """Update an existing Jira issue."""
        self.jira.update_issue(issue_key, fields=fields)

    def add_comment(self, issue_key: str, comment: str) -> dict[str, Any]:
        """Add a comment to a Jira issue."""
        return self.jira.add_comment(issue_key, comment)

    def get_issue_comments(self, issue_key: str) -> list[dict[str, Any]]:
        """Return the list of comments on a Jira issue."""
        data = self.jira.issue(issue_key, fields="comment")
        return ((data.get("fields") or {}).get("comment") or {}).get("comments", [])

    def get_issue_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        """Return available workflow transitions for a Jira issue."""
        data = self.jira.get_issue_transitions(issue_key)
        if isinstance(data, dict):
            return data.get("transitions", [])
        return data or []

    def transition_issue(
        self,
        issue_key: str,
        transition_name: str,
        comment: Optional[str] = None,
    ) -> dict[str, Any]:
        """Move an issue through its workflow by transition name (case-insensitive)."""
        transitions = self.get_issue_transitions(issue_key)
        target = next(
            (t for t in transitions if str(t.get("name", "")).lower() == transition_name.lower()),
            None,
        )
        if target is None:
            available = ", ".join(t.get("name", "?") for t in transitions) or "(none)"
            raise ValueError(
                f"Transition '{transition_name}' not available for {issue_key}. "
                f"Available: {available}"
            )
        if comment:
            self.add_comment(issue_key, comment)
        self.jira.issue_transition(issue_key, target["name"])
        return {"issue_key": issue_key, "transition": target.get("name"), "to_status": (target.get("to") or {}).get("name")}

    def assign_issue(self, issue_key: str, assignee: Optional[str]) -> None:
        """Assign or unassign a Jira issue."""
        self.jira.assign_issue(issue_key, assignee)

    def get_issue_changelog(self, issue_key: str) -> list[dict[str, Any]]:
        """Return the changelog (history) of a Jira issue."""
        data = self.jira.issue(issue_key, expand="changelog")
        return ((data.get("changelog") or {}).get("histories") or [])

    def list_projects(self) -> list[dict[str, Any]]:
        """List all accessible Jira projects."""
        return self.jira.projects()

    def get_project(self, project_key: str) -> dict[str, Any]:
        """Get details of a Jira project."""
        return self.jira.project(project_key)

    def get_user(self, username: str) -> dict[str, Any]:
        """Get a Jira user profile by username or accountId."""
        try:
            return self.jira.user(username=username)
        except TypeError:
            return self.jira.user(account_id=username)

    def get_my_issues(
        self,
        project_key: Optional[str] = None,
        statuses: Optional[list[str]] = None,
        limit: int = 50,
        start: int = 0,
    ) -> dict[str, Any]:
        """Issues assigned to the authenticated user, newest first."""
        clauses = ["assignee = currentUser()"]
        if project_key:
            clauses.append(f"project = {project_key}")
        if statuses:
            quoted = ", ".join(f'"{s}"' for s in statuses)
            clauses.append(f"status in ({quoted})")
        jql = " AND ".join(clauses) + " ORDER BY priority DESC, updated DESC"
        return self.search_issues(jql, limit=limit, start=start)

    # Agile
    def list_agile_boards(
        self,
        project_key: Optional[str] = None,
        board_type: Optional[str] = None,
        limit: int = 50,
        start: int = 0,
    ) -> dict[str, Any]:
        """List agile boards."""
        return self.jira.get_all_agile_boards(
            board_name=None,
            project_key=project_key,
            board_type=board_type,
            start=start,
            limit=limit,
        )

    def list_board_sprints(
        self,
        board_id: int,
        state: str = "active",
        limit: int = 50,
        start: int = 0,
    ) -> dict[str, Any]:
        """List sprints on a board."""
        api_state = None if state == "all" else state
        return self.jira.get_all_sprints_from_board(
            board_id, state=api_state, start=start, limit=limit
        )

    def list_sprint_issues(
        self,
        sprint_id: int,
        limit: int = 50,
        start: int = 0,
    ) -> dict[str, Any]:
        """List issues in a sprint."""
        return self.jira.get_sprint_issues(sprint_id, start=start, limit=limit)

    def summarize_issue(
        self,
        issue_key: str,
        include_comments: bool = True,
        include_changelog: bool = True,
        include_transitions: bool = True,
        comment_limit: int = 20,
    ) -> dict[str, Any]:
        """Return issue fields + comments + changelog + transitions in one call."""
        expand_parts = []
        if include_changelog:
            expand_parts.append("changelog")
        issue = self.jira.issue(issue_key, expand=",".join(expand_parts) or None)
        result: dict[str, Any] = {"issue": issue}
        if include_comments:
            comments = ((issue.get("fields") or {}).get("comment") or {}).get("comments", [])
            result["comments"] = comments[:comment_limit]
        if include_changelog:
            result["changelog"] = (issue.get("changelog") or {}).get("histories", [])
        if include_transitions:
            result["transitions"] = self.get_issue_transitions(issue_key)
        return result

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

    def remove_page_label(self, page_id: str, label: str) -> None:
        """Remove a label from a Confluence page."""
        self.confluence.remove_page_label(page_id, label)

    def delete_page(self, page_id: str) -> None:
        """Delete a Confluence page."""
        self.confluence.remove_page(page_id)

    def search_cql(self, cql: str, limit: int = 20, start: int = 0) -> dict[str, Any]:
        """Search Confluence with a CQL query."""
        return self.confluence.cql(cql, limit=limit, start=start)

    def get_page_children(self, page_id: str, limit: int = 25, start: int = 0) -> list[dict[str, Any]]:
        """List child pages of a Confluence page."""
        return self.confluence.get_page_child_by_type(
            page_id, type="page", start=start, limit=limit
        )

    def get_page_comments(self, page_id: str) -> list[dict[str, Any]]:
        """List comments on a Confluence page."""
        data = self.confluence.get_page_comments(content_id=page_id, expand="body.view")
        if isinstance(data, dict):
            return data.get("results", [])
        return data or []

    def add_page_comment(self, page_id: str, comment: str) -> dict[str, Any]:
        """Add a comment to a Confluence page."""
        return self.confluence.add_comment(page_id=page_id, text=comment)

    def get_page_labels(self, page_id: str) -> list[dict[str, Any]]:
        """List labels applied to a Confluence page."""
        data = self.confluence.get_page_labels(page_id)
        if isinstance(data, dict):
            return data.get("results", [])
        return data or []

    def list_spaces(
        self, limit: int = 25, start: int = 0, space_type: Optional[str] = None
    ) -> dict[str, Any]:
        """List Confluence spaces."""
        kwargs: dict[str, Any] = {"limit": limit, "start": start}
        if space_type:
            kwargs["space_type"] = space_type
        return self.confluence.get_all_spaces(**kwargs)

    def get_page_history(self, page_id: str) -> dict[str, Any]:
        """Return version history information for a Confluence page."""
        return self.confluence.history(page_id)

    def get_page_attachments(self, page_id: str) -> list[dict[str, Any]]:
        """List attachments on a Confluence page."""
        data = self.confluence.get_attachments_from_content(page_id=page_id)
        if isinstance(data, dict):
            return data.get("results", [])
        return data or []
