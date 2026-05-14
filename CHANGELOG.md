# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-05-14

### Added
- Initial release of `mcp-jira-confluence`.
- `JiraConfluenceClient` — unified client wrapping
  [`atlassian-python-api`](https://atlassian-python-api.readthedocs.io/) for
  Jira and Confluence REST APIs.
- `ProxyConfig` with configurable per-domain bypass (wildcards supported) and
  loading from the `MCP_BYPASS_DOMAINS` environment variable.
- `JiraConfig` and `ConfluenceConfig` loaded from environment variables.
- Personal Access Token (PAT) authentication, with optional Basic Auth fallback.
- Self-signed certificate handling (SSL verification disabled by default).
- MCP server implementation using the official `mcp` SDK over stdio.
- Tools exposed by the MCP server: `jira_get_issue`, `jira_search`,
  `jira_add_comment`, `confluence_get_page`, `confluence_update_page`,
  `confluence_create_page`.
- GitHub Actions workflow for CI on Python 3.9–3.13.
- GitHub Actions workflow for PyPI publishing via Trusted Publishing.

### Background
This package solves a recurring problem in corporate networks: an SSH tunnel or
proxy intended for a cloud API silently intercepts traffic to on-prem Jira and
Confluence, causing timeouts. The built-in proxy bypass mechanism prevents this
for any internal domain configured via `ProxyConfig.bypass_domains` or the
`MCP_BYPASS_DOMAINS` environment variable.

[Unreleased]: https://github.com/mshegolev/mcp-jira-confluence/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/mshegolev/mcp-jira-confluence/releases/tag/v0.1.0
