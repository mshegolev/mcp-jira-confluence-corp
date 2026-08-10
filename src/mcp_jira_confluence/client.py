"""Unified client for Jira and Confluence with corporate proxy support."""

import os
from typing import Any

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
        jira_config: JiraConfig | None = None,
        confluence_config: ConfluenceConfig | None = None,
        proxy_config: ProxyConfig | None = None,
    ):
        self.jira_config = jira_config or JiraConfig.from_env()
        self.confluence_config = confluence_config or ConfluenceConfig.from_env()
        self.proxy_config = proxy_config or ProxyConfig()

        self._clear_proxy_env()

        self._jira: Jira | None = None
        self._confluence: Confluence | None = None

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
        self, issue_key: str, fields: list[str] | None = None, expand: str | None = None
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
        fields: list[str] | None = None,
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
        comment: str | None = None,
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
        return {
            "issue_key": issue_key,
            "transition": target.get("name"),
            "to_status": (target.get("to") or {}).get("name"),
        }

    def assign_issue(self, issue_key: str, assignee: str | None) -> None:
        """Assign or unassign a Jira issue."""
        self.jira.assign_issue(issue_key, assignee)

    def get_issue_changelog(self, issue_key: str) -> list[dict[str, Any]]:
        """Return the changelog (history) of a Jira issue."""
        data = self.jira.issue(issue_key, expand="changelog")
        return (data.get("changelog") or {}).get("histories") or []

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
        project_key: str | None = None,
        statuses: list[str] | None = None,
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

    def get_all_fields(self) -> list[dict[str, Any]]:
        """Return the global Jira field catalog."""
        return self.jira.get_all_fields() or []

    def get_project_issue_types(self, project_key: str) -> list[dict[str, Any]]:
        """Return issue types available for issue creation in a project."""
        data = self.jira.issue_createmeta_issuetypes(project_key)
        return self._extract_issue_types(data, project_key)

    def get_project_issue_type_fields(self, project_key: str, issue_type_id: str) -> dict[str, Any]:
        """Return create metadata fields for a project issue type."""
        return self.jira.issue_createmeta_fieldtypes(project_key, issue_type_id) or {}

    def get_issue_editmeta(self, issue_key: str) -> dict[str, Any]:
        """Return edit metadata for a Jira issue."""
        return self.jira.issue_editmeta(issue_key) or {}

    def get_issue_fields(self, issue_key: str) -> dict[str, Any]:
        """Return current issue field values for sampling field payload shapes."""
        data = self.jira.issue_fields(issue_key) or {}
        if isinstance(data, dict) and isinstance(data.get("fields"), dict):
            return data["fields"]
        return data if isinstance(data, dict) else {}

    def build_field_map(
        self,
        project_key: str | None = None,
        issue_key: str | None = None,
        max_rows: int = 50,
    ) -> dict[str, Any]:
        """Build a normalized Jira field map from global, create, and edit metadata.

        ``project_key`` adds create metadata per issue type. ``issue_key`` adds
        edit metadata and current sample values. JSON responses include all rows;
        markdown renderers can use ``max_rows`` to keep tables readable.
        """
        rows: list[dict[str, Any]] = []

        global_fields = self.get_all_fields()
        for field in global_fields:
            if not isinstance(field, dict):
                continue
            rows.append(
                self._field_map_row(
                    context="global",
                    context_label="Global field catalog",
                    project_key=None,
                    issue_key=None,
                    issue_type=None,
                    field_id=str(field.get("id") or field.get("key") or ""),
                    field_meta=field,
                )
            )

        issue_types: list[dict[str, Any]] = []
        if project_key:
            issue_types = self.get_project_issue_types(project_key)
            for issue_type in issue_types:
                issue_type_id = str(issue_type.get("id") or "")
                if not issue_type_id:
                    continue
                fields_meta = self.get_project_issue_type_fields(project_key, issue_type_id)
                for field_id, field_meta in self._extract_fields(fields_meta).items():
                    rows.append(
                        self._field_map_row(
                            context="create",
                            context_label="Project create metadata",
                            project_key=project_key,
                            issue_key=None,
                            issue_type=issue_type,
                            field_id=field_id,
                            field_meta=field_meta,
                        )
                    )

        if issue_key:
            editmeta = self.get_issue_editmeta(issue_key)
            issue_fields = self.get_issue_fields(issue_key)
            for field_id, field_meta in self._extract_fields(editmeta).items():
                rows.append(
                    self._field_map_row(
                        context="edit",
                        context_label="Issue edit metadata",
                        project_key=project_key,
                        issue_key=issue_key,
                        issue_type=None,
                        field_id=field_id,
                        field_meta=field_meta,
                        sample_value=issue_fields.get(field_id),
                    )
                )

        return {
            "scope": {"project_key": project_key, "issue_key": issue_key},
            "summary": {
                "global_field_count": len(global_fields),
                "project_issue_type_count": len(issue_types),
                "project_field_row_count": sum(1 for row in rows if row["context"] == "create"),
                "edit_field_row_count": sum(1 for row in rows if row["context"] == "edit"),
                "total_rows": len(rows),
            },
            "project_issue_types": issue_types,
            "max_rows": max_rows,
            "rows": rows,
        }

    @staticmethod
    def _extract_issue_types(data: Any, project_key: str) -> list[dict[str, Any]]:
        """Normalize Jira createmeta issue type payloads across API variants."""
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []
        if isinstance(data.get("issuetypes"), list):
            return [item for item in data["issuetypes"] if isinstance(item, dict)]
        projects = data.get("projects")
        if isinstance(projects, list):
            for project in projects:
                if not isinstance(project, dict):
                    continue
                if project.get("key") == project_key or len(projects) == 1:
                    issue_types = project.get("issuetypes") or []
                    return [item for item in issue_types if isinstance(item, dict)]
        values = data.get("values")
        if isinstance(values, list):
            return [item for item in values if isinstance(item, dict)]
        return []

    @staticmethod
    def _extract_fields(data: Any) -> dict[str, dict[str, Any]]:
        """Normalize metadata payloads to ``field_id -> field metadata``."""
        if not isinstance(data, dict):
            return {}
        fields = data.get("fields")
        if isinstance(fields, dict):
            return {str(key): value for key, value in fields.items() if isinstance(value, dict)}

        projects = data.get("projects")
        if isinstance(projects, list):
            for project in projects:
                if not isinstance(project, dict):
                    continue
                issue_types = project.get("issuetypes") or []
                for issue_type in issue_types:
                    if not isinstance(issue_type, dict):
                        continue
                    fields = issue_type.get("fields")
                    if isinstance(fields, dict):
                        return {
                            str(key): value
                            for key, value in fields.items()
                            if isinstance(value, dict)
                        }
        return {}

    @staticmethod
    def _field_map_row(
        *,
        context: str,
        context_label: str,
        project_key: str | None,
        issue_key: str | None,
        issue_type: dict[str, Any] | None,
        field_id: str,
        field_meta: dict[str, Any],
        sample_value: Any = None,
    ) -> dict[str, Any]:
        """Normalize one Jira field metadata item for table rendering."""
        schema = field_meta.get("schema") or {}
        operations = field_meta.get("operations") or []
        allowed_values = field_meta.get("allowedValues") or []
        schema_custom = schema.get("custom")
        field_name = field_meta.get("name") or field_meta.get("fieldName") or field_id
        return {
            "context": context,
            "context_label": context_label,
            "project_key": project_key,
            "issue_key": issue_key,
            "issue_type_id": (issue_type or {}).get("id"),
            "issue_type_name": (issue_type or {}).get("name"),
            "field_id": field_id,
            "field_name": field_name,
            "kind": "custom" if field_id.startswith("customfield_") or schema_custom else "system",
            "schema_type": schema.get("type"),
            "schema_items": schema.get("items"),
            "schema_custom": schema_custom,
            "required": field_meta.get("required"),
            "operations": operations,
            "allowed_values": allowed_values,
            "allowed_values_count": (
                len(allowed_values) if isinstance(allowed_values, list) else None
            ),
            "sample_value": sample_value,
        }

    # Agile
    def list_agile_boards(
        self,
        project_key: str | None = None,
        board_type: str | None = None,
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

    def get_remote_links(self, issue_key: str) -> list[dict[str, Any]]:
        """Return Jira 'remote' issue links (web links, Confluence links, etc.)."""
        try:
            data = self.jira.get_issue_remote_links(issue_key)
        except AttributeError:
            data = self.jira.get(f"rest/api/2/issue/{issue_key}/remotelink")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("issues") or data.get("values") or []
        return []

    def get_active_sprint_for_board(self, board_id: int) -> dict[str, Any] | None:
        """Return the first active sprint of a board, or None."""
        data = self.list_board_sprints(board_id, state="active", limit=1, start=0)
        sprints = data.get("values", []) if isinstance(data, dict) else (data or [])
        return sprints[0] if sprints else None

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
        parent_id: str | None = None,
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

    def get_page_children(
        self, page_id: str, limit: int = 25, start: int = 0
    ) -> list[dict[str, Any]]:
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
        self, limit: int = 25, start: int = 0, space_type: str | None = None
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
