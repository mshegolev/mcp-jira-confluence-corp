# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Entry-point smoke tests** (`tests/test_entrypoint.py`, 8 tests). Before them,
  coverage reported **0%** for `server.py`, `jira_tools.py`,
  `confluence_tools.py`, `workflow_tools.py` and `prompts.py` — not thinly
  covered, never imported. The suite could be fully green while the
  `mcp-jira-confluence-corp` console script was dead on arrival, which is what
  `mcp` 2.0 removing `mcp.server.fastmcp` did. The tests walk the path a real
  client walks: `console_scripts` metadata → `server:main` → `create_server()` →
  all four `register_*` calls → `mcp.run()` over stdio → clean exit on EOF, plus
  protocol-level `list_tools()` / `list_prompts()`, a stdout-stays-clean check
  (stdio owns stdout), a no-configuration-required check, and an assertion that
  building the server makes no network call. Offline; no PAT, no Atlassian host.
  Coverage of `server.py` 0% → 71%, total 37% → 50%.

### Fixed
- **CI could not fail on a failing test suite.** `pytest` ran with
  `continue-on-error: true`, so a red suite left the job green — the one thing
  the job exists to prevent. Now blocking.
- **The `3.9` matrix leg took the whole matrix down.** `requires-python` is
  `>=3.10` (and `mcp` requires `>=3.10`), so 3.9 failed at `pip install` on
  every run this repo has ever had; with `fail-fast` at its default the other
  four legs were cancelled before they ran. Leg removed, `fail-fast: false`
  added so no single leg can mask the rest again.
- **`black --check` was blocking while `pytest` was not.** It flags 2 files
  (`config.py`, `confluence_tools.py`) of pre-existing drift from a newer black,
  making every run red on cosmetics. Now advisory; re-arm it in the commit that
  reformats those two files.

### Changed
- `[tool.ruff]`/`[tool.black]` `target-version` and `[tool.mypy]`
  `python_version` raised from 3.9 to 3.10, matching `requires-python`.
  Consequent PEP 604 modernisation (`Optional[X]` → `X | None`) applied across
  `client.py`, `config.py` and `models.py`.

## [0.2.2] - 2026-08-10

### Fixed
- **Pin `mcp` to `>=1.2,<2`.** `mcp 2.0` removed `mcp.server.fastmcp`, which this
  server imports in six modules. The unbounded `mcp>=1.0.0` let a clean
  `pip install -e '.[dev]'` resolve `mcp 2.0`, and the
  `mcp-jira-confluence-corp` console script then died at import with
  `ModuleNotFoundError: No module named 'mcp.server.fastmcp'`. The unit tests
  did not catch it — none of them import the server — so the package installed
  and tested green while being unrunnable; from an MCP client the failure
  surfaced as an opaque transport error.
- The lower bound was wrong as well: `FastMCP` first shipped in `mcp 1.2.0`
  (`mcp 1.0.x` / `1.1.x` have no `mcp.server.fastmcp`), so the declared floor of
  `1.0.0` could never have worked. Raised `1.0.0` → `1.2`.

## [0.2.1] - 2026-06-23

### Added
- `jira_field_map` read-only tool for scanning Jira field IDs, names, schemas,
  allowed-value counts, create metadata, edit metadata, and current issue sample
  values. It supports global catalog mode, project-scoped create metadata, and
  issue-scoped edit metadata for safe custom-field updates.

### Changed
- Package metadata now requires Python >=3.10, matching the installed
  `mcp>=1.0.0` dependency constraints.

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

[Unreleased]: https://github.com/mshegolev/mcp-jira-confluence-corp/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/mshegolev/mcp-jira-confluence-corp/compare/v0.2.0...v0.2.2
[0.2.1]: https://github.com/mshegolev/mcp-jira-confluence-corp/compare/v0.2.0...v0.2.1
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

[0.1.0]: https://github.com/mshegolev/mcp-jira-confluence-corp/releases/tag/v0.1.0
