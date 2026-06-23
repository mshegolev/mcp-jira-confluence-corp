"""MCP server for Atlassian Jira and Confluence with corporate proxy support."""

__version__ = "0.2.1"
__author__ = "Mikhail Shegolev"

from .client import JiraConfluenceClient
from .config import ConfluenceConfig, JiraConfig, ProxyConfig

__all__ = [
    "JiraConfluenceClient",
    "ProxyConfig",
    "JiraConfig",
    "ConfluenceConfig",
]
