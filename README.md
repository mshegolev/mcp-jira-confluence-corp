# mcp-jira-confluence-corp

[![PyPI version](https://img.shields.io/pypi/v/mcp-jira-confluence-corp.svg)](https://pypi.org/project/mcp-jira-confluence-corp/)
[![Python versions](https://img.shields.io/pypi/pyversions/mcp-jira-confluence-corp.svg)](https://pypi.org/project/mcp-jira-confluence-corp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/mshegolev/mcp-jira-confluence-corp/actions/workflows/ci.yml/badge.svg)](https://github.com/mshegolev/mcp-jira-confluence-corp/actions/workflows/ci.yml)
[![Glama MCP Server](https://glama.ai/mcp/servers/mshegolev/mcp-jira-confluence-corp/badge)](https://glama.ai/mcp/servers/mshegolev/mcp-jira-confluence-corp)

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

`mcp-jira-confluence-corp` addresses all three by:

- Clearing `HTTP_PROXY`-style environment variables on client construction.
- Listing internal domains that should bypass any proxy (via the
  `MCP_BYPASS_DOMAINS` environment variable or `ProxyConfig.bypass_domains`).
- Disabling SSL verification by default (configurable via `verify_ssl`).
- Accepting PATs through `JIRA_PERSONAL_TOKEN` / `CONFLUENCE_PERSONAL_TOKEN`.

## Installation

```bash
pip install mcp-jira-confluence-corp
```

Or run it without installing using [`uvx`](https://github.com/astral-sh/uv):

```bash
uvx mcp-jira-confluence-corp
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
      "args": ["mcp-jira-confluence-corp"],
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

### Jira (read-only)
| Tool                              | Description                                  |
|-----------------------------------|----------------------------------------------|
| `jira_get_issue`                  | Get a Jira issue by key                      |
| `jira_search_issues`              | Search issues using JQL with pagination      |
| `jira_get_issue_comments`         | List comments on an issue                    |
| `jira_get_issue_transitions`      | List available workflow transitions          |
| `jira_get_issue_changelog`        | Get issue history (status, field changes)    |
| `jira_list_projects`              | List accessible projects                     |
| `jira_get_project`                | Get details of a specific project            |
| `jira_get_user`                   | Get a user profile                           |
| `jira_field_map`                  | Map Jira field IDs, names, schemas, and editability |

### Jira (write)
| Tool                              | Description                                  |
|-----------------------------------|----------------------------------------------|
| `jira_create_issue`               | Create a new issue                           |
| `jira_update_issue`               | Update fields of an existing issue           |
| `jira_add_comment`                | Add a comment to an issue                    |
| `jira_transition_issue`           | Move an issue through its workflow           |
| `jira_assign_issue`               | Assign or unassign an issue                  |

### Confluence (read-only)
| Tool                              | Description                                  |
|-----------------------------------|----------------------------------------------|
| `confluence_get_page`             | Get a page by ID                             |
| `confluence_get_page_by_title`    | Get a page by title and space                |
| `confluence_search`               | Search using CQL                             |
| `confluence_get_page_children`    | List child pages                             |
| `confluence_get_page_comments`    | List page comments                           |
| `confluence_get_page_labels`      | List labels applied to a page                |
| `confluence_list_spaces`          | List Confluence spaces                       |

### Confluence (write)
| Tool                              | Description                                  |
|-----------------------------------|----------------------------------------------|
| `confluence_create_page`          | Create a new page                            |
| `confluence_update_page`          | Update an existing page                      |
| `confluence_add_comment`          | Add a comment to a page                      |
| `confluence_add_label`            | Add a label to a page                        |
| `confluence_remove_label`         | Remove a label from a page                   |

All tools support both `markdown` (default) and `json` response formats for
human-readability vs. programmatic consumption.

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

field_map = client.build_field_map(project_key="PROJ", issue_key="PROJ-123")
for row in field_map["rows"]:
    print(row["field_id"], row["field_name"], row["schema_type"])
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
git clone https://github.com/mshegolev/mcp-jira-confluence-corp.git
cd mcp-jira-confluence-corp
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
