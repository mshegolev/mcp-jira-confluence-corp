# mcp-jira-confluence

[![PyPI version](https://img.shields.io/pypi/v/mcp-jira-confluence.svg)](https://pypi.org/project/mcp-jira-confluence/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-jira-confluence.svg)](https://pypi.org/project/mcp-jira-confluence/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/mshegolev/mcp-jira-confluence/actions/workflows/ci.yml/badge.svg)](https://github.com/mshegolev/mcp-jira-confluence/actions/workflows/ci.yml)

A [Model Context Protocol](https://modelcontextprotocol.io/) server for Atlassian
Jira and Confluence, designed for corporate networks. It transparently bypasses
system HTTP proxies for internal domains, handles self-signed certificates, and
supports Personal Access Token (PAT) authentication.

## Why this package exists

Generic MCP servers like `mcp-atlassian` work well against Atlassian Cloud but
struggle inside many corporate environments where:

1. A global `HTTP_PROXY` or `HTTPS_PROXY` (typically an SSH tunnel for a cloud
   API) silently intercepts on-prem traffic and causes timeouts.
2. Internal Jira and Confluence instances use self-signed TLS certificates.
3. The only available credential is a Personal Access Token rather than a
   username/password pair.

`mcp-jira-confluence` addresses all three by:

- Clearing `HTTP_PROXY`-style environment variables on client construction.
- Listing internal domains that should bypass any proxy (via the
  `MCP_BYPASS_DOMAINS` environment variable or `ProxyConfig.bypass_domains`).
- Disabling SSL verification by default (configurable via `verify_ssl`).
- Accepting PATs through `JIRA_PERSONAL_TOKEN` / `CONFLUENCE_PERSONAL_TOKEN`.

## Installation

```bash
pip install mcp-jira-confluence
```

Or run it without installing using [`uvx`](https://github.com/astral-sh/uv):

```bash
uvx mcp-jira-confluence
```

## Configuration

The server is configured through environment variables:

| Variable                       | Description                                            |
|--------------------------------|--------------------------------------------------------|
| `JIRA_URL`                     | Base URL of your Jira instance                         |
| `JIRA_PERSONAL_TOKEN`          | Personal Access Token for Jira                         |
| `JIRA_USERNAME` / `JIRA_TOKEN` | Optional Basic Auth pair (alternative to PAT)          |
| `CONFLUENCE_URL`               | Base URL of your Confluence instance                   |
| `CONFLUENCE_PERSONAL_TOKEN`    | Personal Access Token for Confluence                   |
| `MCP_BYPASS_DOMAINS`           | Comma-separated list of internal domains to bypass any proxy. Supports `*.example.com` wildcards. |

### MCP client configuration

```json
{
  "mcpServers": {
    "jira-confluence": {
      "command": "uvx",
      "args": ["mcp-jira-confluence"],
      "env": {
        "JIRA_URL": "https://jira.example.com",
        "JIRA_PERSONAL_TOKEN": "<your-token>",
        "CONFLUENCE_URL": "https://confluence.example.com",
        "CONFLUENCE_PERSONAL_TOKEN": "<your-token>",
        "MCP_BYPASS_DOMAINS": "*.example.com,internal.corp",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": ""
      }
    }
  }
}
```

## Available tools

| Tool                       | Description                            |
|----------------------------|----------------------------------------|
| `jira_get_issue`           | Get a Jira issue by key                |
| `jira_search`              | Search Jira issues using JQL           |
| `jira_add_comment`         | Add a comment to a Jira issue          |
| `confluence_get_page`      | Get a Confluence page by ID            |
| `confluence_update_page`   | Update an existing Confluence page     |
| `confluence_create_page`   | Create a new Confluence page           |

## Programmatic usage

`JiraConfluenceClient` is a thin wrapper around
[`atlassian-python-api`](https://atlassian-python-api.readthedocs.io/) and is
fully usable outside of the MCP server.

```python
from mcp_jira_confluence import JiraConfluenceClient

client = JiraConfluenceClient()

issue = client.get_issue("PROJ-123")
print(issue["fields"]["summary"])

page = client.get_page("123456")
print(page["title"])

client.update_page(
    page_id="123456",
    title="Release notes",
    body="<p>Updated content in Confluence Storage Format.</p>",
)
```

### Customizing proxy bypass

```python
from mcp_jira_confluence import JiraConfluenceClient, ProxyConfig

proxy_config = ProxyConfig(
    bypass_domains=["*.example.com", "internal.corp"],
    verify_ssl=False,
)
client = JiraConfluenceClient(proxy_config=proxy_config)
```

## Development

```bash
git clone https://github.com/mshegolev/mcp-jira-confluence.git
cd mcp-jira-confluence
pip install -e ".[dev]"

pytest tests/
ruff check src/
black --check src/
```

## Releasing

This project uses [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/),
so no API tokens are stored in GitHub.

1. Bump the version in `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Tag the release: `git tag v0.1.1 && git push --tags`.
4. Create a GitHub release — the publish workflow runs automatically.

## License

[MIT](LICENSE)

## Author

Mikhail Shegolev — [mshegolev@gmail.com](mailto:mshegolev@gmail.com)
