# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-05-14

### Added
- **2 new workflow tools** (inspired by `akhilthomas236/jira-confluence-mcp`):
  - `jira_extract_links` — pull every Confluence / Git URL out of an issue's
    description, comments, and remote links; classified and de-duplicated.
  - `jira_daily_standup_summary` — one-call standup picture of a sprint:
    progress %, status counts, per-assignee workload, blockers.
- **6 MCP prompts** for opinionated workflows. Prompts compose multiple tool
  calls and encode reusable agent procedures:
  - `confluence_create_release_notes` — generate release notes from Jira
    issues filtered by `fixVersion` and publish as a Confluence page.
  - `confluence_document_feature` — draft a feature page from a Jira epic /
    story, pulling related Git repos and Confluence links automatically.
  - `confluence_audit_page` — assess a page for staleness, missing metadata,
    open comments, and orphan children; produces a written recommendation.
  - `confluence_summarize_space` — survey an entire space: page counts,
    recently updated, stale, top contributors.
  - `jira_sprint_report` — sprint review / retro-ready report.
  - `jira_triage_my_issues` — triage the user's own assigned issues with a
    "now / stale / blocked / defer" plan.

### Changed
- Total tool count: 34 (was 32 in v0.1.0).
- Total prompt count: 6 (was 0 in v0.1.0).

[Unreleased]: https://github.com/mshegolev/mcp-jira-confluence-corp/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/mshegolev/mcp-jira-confluence-corp/releases/tag/v0.2.0

## [0.1.0] - 2026-05-14

### Added
- Initial public release of `mcp-jira-confluence-corp` on PyPI.
- `JiraConfluenceClient` — unified client wrapping
  [`atlassian-python-api`](https://atlassian-python-api.readthedocs.io/) for
  Jira and Confluence REST APIs.
- `ProxyConfig` with configurable per-domain bypass (wildcards supported) and
  loading from the `MCP_BYPASS_DOMAINS` environment variable.
- `JiraConfig` and `ConfluenceConfig` loaded from environment variables.
- Personal Access Token (PAT) authentication, with optional Basic Auth fallback.
- Self-signed certificate handling (SSL verification disabled by default).
- FastMCP-based MCP server with stdio and streamable HTTP transports.

### Tools (32 total)

**Jira read-only (10):**
- `jira_get_issue`, `jira_search_issues`, `jira_get_issue_comments`,
  `jira_get_issue_transitions`, `jira_get_issue_changelog`,
  `jira_list_projects`, `jira_get_project`, `jira_get_user`,
  `jira_get_my_issues`, `jira_summarize_issue`

**Jira agile (3):**
- `jira_list_agile_boards`, `jira_list_board_sprints`, `jira_list_sprint_issues`

**Jira write (5):**
- `jira_create_issue`, `jira_update_issue`, `jira_add_comment`,
  `jira_transition_issue`, `jira_assign_issue`

**Confluence read-only (9):**
- `confluence_get_page`, `confluence_get_page_by_title`, `confluence_search`,
  `confluence_get_page_children`, `confluence_get_page_comments`,
  `confluence_get_page_labels`, `confluence_list_spaces`,
  `confluence_get_page_history`, `confluence_get_page_attachments`

**Confluence write (5):**
- `confluence_create_page`, `confluence_update_page`,
  `confluence_add_comment`, `confluence_add_label`, `confluence_remove_label`

### Features
- Every tool accepts a typed Pydantic v2 input model with field constraints.
- Every tool supports both `markdown` (default, human-readable) and `json`
  response formats.
- Tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`,
  `openWorldHint`) are set on every tool to help clients reason about safety.
- Pagination on every list endpoint with `has_more` / `next_offset`.
- Centralized error handling with actionable suggestions.
- 14 unit tests covering config, auth precedence, and proxy bypass.
- Evaluation suite (`evals/evaluation.xml`) with 10 realistic Q&A pairs.

### Infrastructure
- GitHub Actions workflow for CI on Python 3.9–3.13.
- GitHub Actions workflow for PyPI publishing via Trusted Publishing.

### Background
This package solves a recurring problem in corporate networks: an SSH tunnel or
proxy intended for a cloud API silently intercepts traffic to on-prem Jira and
Confluence, causing timeouts. The built-in proxy bypass mechanism prevents this
for any internal domain configured via `ProxyConfig.bypass_domains` or the
`MCP_BYPASS_DOMAINS` environment variable.

[Unreleased]: https://github.com/mshegolev/mcp-jira-confluence-corp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mshegolev/mcp-jira-confluence-corp/releases/tag/v0.1.0
