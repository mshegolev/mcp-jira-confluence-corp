# MCP Jira/Confluence

Model Context Protocol server for Jira and Confluence APIs with built-in MTS corporate network proxy support.

## Features

- ✅ Automatic proxy bypass for internal MTS domains (`*.mts.ru`, `*.services.mts.ru`)
- ✅ Self-signed certificate handling (SSL verification disabled by default)
- ✅ Token-based and username/password authentication
- ✅ Unified client for both Jira and Confluence
- ✅ Environment variable configuration
- ✅ MCP stdio protocol support

## Installation

```bash
# Using uvx (recommended)
uvx --from mcp-jira-confluence mcp-jira-confluence

# Or pip install locally
pip install -e .
mcp-jira-confluence
```

## Configuration

### Environment Variables

```bash
# Jira
export JIRA_URL="https://jira.mts.ru"
export JIRA_PERSONAL_TOKEN="your_token_here"
# or
export JIRA_USERNAME="username"
export JIRA_TOKEN="password_or_token"

# Confluence
export CONFLUENCE_URL="https://confluence.mts.ru"
export CONFLUENCE_PERSONAL_TOKEN="your_token_here"
# or
export CONFLUENCE_USERNAME="username"
export CONFLUENCE_TOKEN="password_or_token"
```

### .mcp.json Example

```json
{
  "mcpServers": {
    "jira-confluence": {
      "type": "stdio",
      "command": "uvx",
      "args": [
        "--from",
        "mcp-jira-confluence",
        "mcp-jira-confluence"
      ],
      "env": {
        "JIRA_URL": "https://jira.mts.ru",
        "JIRA_PERSONAL_TOKEN": "your_jira_token",
        "CONFLUENCE_URL": "https://confluence.mts.ru",
        "CONFLUENCE_PERSONAL_TOKEN": "your_confluence_token",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "http_proxy": "",
        "https_proxy": ""
      }
    }
  }
}
```

## How It Works

### Proxy Bypass Logic

The client automatically:

1. **Clears global proxy env vars** (`HTTP_PROXY`, `HTTPS_PROXY`, etc.) to prevent interference
2. **Detects internal MTS domains** using wildcard matching:
   - `*.mts.ru`
   - `*.services.mts.ru`
   - `confluence.mts.ru`
   - `jira.mts.ru`
   - And others (see `ProxyConfig.bypass_domains`)
3. **Routes internal requests directly** without proxy tunnel
4. **Handles self-signed certificates** by default (MTS uses WinCA G3)

This solves the common issue where SSH tunnels intended for cloud APIs (Anthropic, etc.) accidentally intercept and block internal Jira/Confluence requests.

### Client Architecture

```
JiraConfluenceClient
├── ProxyConfig (handles domain-based proxy bypass)
├── JiraConfig (loads from JIRA_* env vars)
├── ConfluenceConfig (loads from CONFLUENCE_* env vars)
├── atlassian.Jira (initialized with proxy-cleared env)
└── atlassian.Confluence (initialized with proxy-cleared env)
```

## Available Tools (MCP)

### Jira

- `jira/get_issue` - Get issue details by key
- `jira/search` - Search issues using JQL
- `jira/create_issue` - Create new issue
- `jira/update_issue` - Update issue fields
- `jira/add_comment` - Add comment to issue

### Confluence

- `confluence/get_page` - Get page by ID
- `confluence/update_page` - Update page content
- `confluence/create_page` - Create new page
- `confluence/delete_page` - Delete page
- `confluence/add_label` - Add label to page

## Troubleshooting

### 401 Authentication Error

1. **Verify token format**: Personal tokens should be long opaque strings, not `username:password`
2. **Check environment variables**: `echo $JIRA_PERSONAL_TOKEN`
3. **Verify proxy settings**: Run `echo $HTTP_PROXY` (should be empty)

### Timeout on Confluence/Jira requests

1. **Clear proxy vars first**: `unset HTTP_PROXY HTTPS_PROXY`
2. **Check SSH tunnel status**: `lsof -i :11112` (for HTTP CONNECT tunnel)
3. **Verify network access**: `curl -sk https://confluence.mts.ru/wiki`

### SSL Certificate Error

Set `CONFLUENCE_SSL_VERIFY=false` or `JIRA_SSL_VERIFY=false` in `.mcp.json` env.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Format code
black src/ tests/
ruff check --fix src/ tests/

# Build distribution
hatchling build
```

## License

MIT

## Author

Mikhail Shegolev (mshegolev@gmail.com)
