"""Pydantic v2 input models for all MCP tools.

Every tool accepts a single Pydantic model that:
- Validates and normalizes input
- Provides the inputSchema FastMCP exposes to clients
- Documents field constraints and examples inline
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResponseFormat(str, Enum):
    """Output format requested by the caller."""

    JSON = "json"
    MARKDOWN = "markdown"


class _StrictModel(BaseModel):
    """Base for all tool input models with safe defaults."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )


# ---------------------------------------------------------------------------
# Jira input models
# ---------------------------------------------------------------------------

class JiraIssueKey(_StrictModel):
    """Input for tools that act on a single Jira issue."""

    issue_key: str = Field(
        ...,
        description="Jira issue key, e.g. 'PROJ-123'",
        min_length=2,
        max_length=64,
        pattern=r"^[A-Za-z][A-Za-z0-9_]*-\d+$",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' for human-readable, 'json' for machine-readable",
    )


class JiraSearchInput(_StrictModel):
    """Input for searching Jira issues via JQL."""

    jql: str = Field(
        ...,
        description="JQL query, e.g. 'project = PROJ AND status = Open'",
        min_length=1,
        max_length=4096,
    )
    limit: int = Field(
        default=20,
        description="Maximum number of issues to return per page",
        ge=1,
        le=100,
    )
    offset: int = Field(
        default=0,
        description="Number of issues to skip (for pagination)",
        ge=0,
    )
    fields: Optional[list[str]] = Field(
        default=None,
        description=(
            "Optional list of issue fields to return (default: a useful subset). "
            "Use ['*all'] to return every field."
        ),
        max_length=50,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="'markdown' or 'json'",
    )

    @field_validator("jql")
    @classmethod
    def _strip_jql(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("JQL cannot be empty")
        return v


class JiraCreateIssueInput(_StrictModel):
    """Input for creating a new Jira issue."""

    project_key: str = Field(..., description="Project key, e.g. 'PROJ'", min_length=1, max_length=32)
    summary: str = Field(..., description="Short summary / title", min_length=1, max_length=255)
    issue_type: str = Field(default="Task", description="Issue type name (e.g. 'Bug', 'Task', 'Story')")
    description: Optional[str] = Field(default=None, description="Optional issue body (Jira wiki/markdown)")
    assignee: Optional[str] = Field(default=None, description="Optional assignee username/accountId")
    labels: Optional[list[str]] = Field(default=None, description="Optional list of labels", max_length=20)
    priority: Optional[str] = Field(default=None, description="Optional priority name (e.g. 'High')")
    extra_fields: Optional[dict] = Field(
        default=None,
        description=(
            "Additional Jira fields by API name, merged into the create request. "
            "Example: {'customfield_10101': 'EPIC-1'}"
        ),
    )


class JiraUpdateIssueInput(_StrictModel):
    """Input for updating fields of an existing Jira issue."""

    issue_key: str = Field(..., description="Issue key, e.g. 'PROJ-123'", pattern=r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
    fields: dict = Field(..., description="Fields to update, by Jira API name", min_length=1)


class JiraCommentInput(_StrictModel):
    """Input for adding a comment to a Jira issue."""

    issue_key: str = Field(..., description="Issue key, e.g. 'PROJ-123'", pattern=r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
    comment: str = Field(..., description="Comment body (Jira wiki markup)", min_length=1, max_length=32768)


class JiraTransitionInput(_StrictModel):
    """Input for transitioning a Jira issue to a new status."""

    issue_key: str = Field(..., description="Issue key, e.g. 'PROJ-123'", pattern=r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
    transition_name: str = Field(
        ...,
        description="Name of the target transition (e.g. 'In Progress', 'Done'). Case-insensitive.",
        min_length=1,
        max_length=128,
    )
    comment: Optional[str] = Field(default=None, description="Optional comment to add with the transition")


class JiraAssignInput(_StrictModel):
    """Input for assigning a Jira issue to a user."""

    issue_key: str = Field(..., description="Issue key, e.g. 'PROJ-123'", pattern=r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
    assignee: Optional[str] = Field(
        default=None,
        description="Username/accountId of the new assignee. Pass null/None to unassign.",
    )


class JiraPagedInput(_StrictModel):
    """Generic paginated input for read-only Jira list endpoints."""

    limit: int = Field(default=50, description="Max items to return", ge=1, le=200)
    offset: int = Field(default=0, description="Items to skip", ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class JiraProjectKey(_StrictModel):
    """Input requiring a Jira project key."""

    project_key: str = Field(..., description="Project key, e.g. 'PROJ'", min_length=1, max_length=32)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class JiraUserInput(_StrictModel):
    """Input for fetching a Jira user."""

    username: str = Field(..., description="Username or accountId", min_length=1, max_length=256)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class JiraMyIssuesInput(_StrictModel):
    """Input for listing issues assigned to the current user."""

    project_key: Optional[str] = Field(
        default=None,
        description="Optional project key to filter by",
        max_length=32,
    )
    statuses: Optional[list[str]] = Field(
        default=None,
        description="Filter by status names (e.g. ['Open', 'In Progress'])",
        max_length=20,
    )
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class JiraSummarizeInput(_StrictModel):
    """Input for a one-shot comprehensive issue summary.

    Combines issue fields, comments, transitions, and changelog in a single
    response so an agent does not have to make four separate calls.
    """

    issue_key: str = Field(..., description="Issue key, e.g. 'PROJ-123'", pattern=r"^[A-Za-z][A-Za-z0-9_]*-\d+$")
    include_comments: bool = Field(default=True, description="Include comments")
    include_changelog: bool = Field(default=True, description="Include change history")
    include_transitions: bool = Field(default=True, description="Include available transitions")
    comment_limit: int = Field(default=20, ge=1, le=100, description="Max comments to include")
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# ---------------------------------------------------------------------------
# Jira agile (boards / sprints) input models
# ---------------------------------------------------------------------------

class JiraAgileBoardsInput(_StrictModel):
    """Input for listing agile boards."""

    project_key: Optional[str] = Field(default=None, description="Filter boards by project key", max_length=32)
    board_type: Optional[str] = Field(
        default=None,
        description="Filter by board type ('scrum' or 'kanban')",
        pattern=r"^(scrum|kanban)$",
    )
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class SprintState(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    FUTURE = "future"
    ALL = "all"


class JiraBoardSprintsInput(_StrictModel):
    """Input for listing sprints on a board."""

    board_id: int = Field(..., description="Board ID (integer)", ge=1)
    state: SprintState = Field(default=SprintState.ACTIVE, description="Sprint state filter")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class JiraSprintIssuesInput(_StrictModel):
    """Input for listing issues in a sprint."""

    sprint_id: int = Field(..., description="Sprint ID (integer)", ge=1)
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# ---------------------------------------------------------------------------
# Confluence extended models
# ---------------------------------------------------------------------------

class ConfluencePageHistoryInput(_StrictModel):
    """Input for fetching a Confluence page's version history."""

    page_id: str = Field(..., description="Page ID", min_length=1, max_length=32)
    limit: int = Field(default=25, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ConfluencePageAttachmentsInput(_StrictModel):
    """Input for listing attachments on a Confluence page."""

    page_id: str = Field(..., description="Page ID", min_length=1, max_length=32)
    limit: int = Field(default=25, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


# ---------------------------------------------------------------------------
# Confluence input models
# ---------------------------------------------------------------------------

class ConfluencePageIdInput(_StrictModel):
    """Input for tools that act on a single Confluence page by ID."""

    page_id: str = Field(..., description="Confluence page ID (numeric string)", min_length=1, max_length=32)
    expand: str = Field(
        default="body.storage,version",
        description="Confluence expand parameter (comma-separated)",
        max_length=256,
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ConfluencePageTitleInput(_StrictModel):
    """Input for getting a page by title and space."""

    space_key: str = Field(..., description="Space key, e.g. 'DOC'", min_length=1, max_length=64)
    title: str = Field(..., description="Exact page title", min_length=1, max_length=512)
    expand: str = Field(default="body.storage,version", max_length=256)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ConfluenceSearchInput(_StrictModel):
    """Input for searching Confluence using CQL."""

    cql: str = Field(
        ...,
        description="CQL query, e.g. 'space = DOC AND type = page AND title ~ \"release\"'",
        min_length=1,
        max_length=4096,
    )
    limit: int = Field(default=20, description="Max results", ge=1, le=100)
    offset: int = Field(default=0, description="Results to skip", ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ConfluenceCreatePageInput(_StrictModel):
    """Input for creating a new Confluence page."""

    space_key: str = Field(..., description="Target space key", min_length=1, max_length=64)
    title: str = Field(..., description="Page title", min_length=1, max_length=512)
    body: str = Field(
        ...,
        description="Page body in Confluence Storage Format (XHTML)",
        min_length=0,
        max_length=2_000_000,
    )
    parent_id: Optional[str] = Field(default=None, description="Optional parent page ID")


class ConfluenceUpdatePageInput(_StrictModel):
    """Input for updating an existing Confluence page."""

    page_id: str = Field(..., description="Page ID to update", min_length=1, max_length=32)
    title: str = Field(..., description="New title", min_length=1, max_length=512)
    body: str = Field(
        ...,
        description="New body in Confluence Storage Format (XHTML)",
        min_length=0,
        max_length=2_000_000,
    )


class ConfluencePageChildrenInput(_StrictModel):
    """Input for listing children of a Confluence page."""

    page_id: str = Field(..., description="Parent page ID", min_length=1, max_length=32)
    limit: int = Field(default=25, description="Max children to return", ge=1, le=200)
    offset: int = Field(default=0, description="Children to skip", ge=0)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)


class ConfluenceLabelInput(_StrictModel):
    """Input for adding/removing a label on a page."""

    page_id: str = Field(..., description="Page ID", min_length=1, max_length=32)
    label: str = Field(..., description="Label name (no spaces)", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_\-]+$")


class ConfluencePageCommentInput(_StrictModel):
    """Input for adding a comment to a Confluence page."""

    page_id: str = Field(..., description="Page ID", min_length=1, max_length=32)
    comment: str = Field(..., description="Comment body (Confluence Storage Format)", min_length=1, max_length=131072)


class ConfluenceListSpacesInput(_StrictModel):
    """Input for listing Confluence spaces."""

    limit: int = Field(default=25, description="Max spaces to return", ge=1, le=200)
    offset: int = Field(default=0, description="Spaces to skip", ge=0)
    space_type: Optional[str] = Field(
        default=None,
        description="Filter by space type ('global' or 'personal')",
        pattern=r"^(global|personal)$",
    )
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN)
